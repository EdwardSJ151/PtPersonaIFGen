"""
Phase 1: Persona-Driven Instruction + Response Generation

Generates IFEval-style training data using a persona-driven two-step approach,
following the TULU 3 / Persona Hub methodology (Chan et al., 2024).

Constraint selection is PROGRAMMATIC: constraints are cycled through in order
(round-robin), so each constraint gets equal coverage across the dataset.
The cycle restarts from the beginning after the last constraint is used.

Step 1: Generate User Instruction (persona-conditioned + constraint-assigned)
    - A constraint is selected deterministically based on item_id % len(constraints)
    - System prompt: a simple instruction-generation prompt
    - User prompt: the persona + the exact constraint phrasing to embed
    - Model generates a natural user instruction that includes the given constraint

Step 2: Generate Assistant Response
    - System prompt: IFEVAL_SYSTEM_PROMPT (constraint-following instructions)
    - User prompt: The generated instruction from Step 1
    - Model generates a response that follows the constraints

This approach:
    - Guarantees uniform constraint coverage across the dataset
    - Provides behavioral/perspective diversity through ~250K personas
    - Ensures constraint consistency between instruction and response
"""

import argparse
import asyncio
from typing import Optional, Dict, Any, Iterator

from openai import AsyncOpenAI
from tqdm import tqdm

from ifeval_persona.main_ifeval_code.config import (
    VLLM_BASE_URL,
    VLLM_API_KEY,
    IFEVAL_SYSTEM_PROMPT,
    PERSONA_DATASET_ID,
    PERSONA_DATASET_SUBSET,
    PERSONA_TEXT_FIELD,
    PHASE1_INSTRUCTION_TEMPERATURE,
    PHASE1_RESPONSE_TEMPERATURE,
    PHASE1_TOP_P,
    PHASE1_MAX_TOKENS_INSTRUCTION,
    PHASE1_MAX_TOKENS_RESPONSE,
    DEFAULT_BATCH_SIZE,
    DEFAULT_NUM_ROWS,
    PHASE1_OUTPUT,
)
from ifeval_persona.main_ifeval_code.utils import get_last_processed_id, write_jsonl_batch


# -----------------------------------------------------------------------
# ASYNC CLIENT
# -----------------------------------------------------------------------
client = AsyncOpenAI(
    base_url=VLLM_BASE_URL,
    api_key=VLLM_API_KEY,
)


# -----------------------------------------------------------------------
# CONSTRAINT SCHEDULE
# Ordered list of (constraint_id, portuguese_phrasing) pairs.
# Constraints are assigned round-robin: item_id % len(CONSTRAINT_SCHEDULE).
# -----------------------------------------------------------------------
CONSTRAINT_SCHEDULE = [
    # ---- Original IFEval constraints ----
    (
        "language:response_language",
        'Sua resposta INTEIRA deve estar em português, nenhum outro idioma é permitido.',
    ),
    (
        "length_constraints:number_sentences",
        'Sua resposta deve conter pelo menos 5 frases.',
    ),
    (
        "detectable_content:number_placeholders",
        'A resposta deve conter pelo menos 2 placeholders representados por colchetes, como [endereço].',
    ),
    (
        "detectable_format:number_bullet_lists",
        'Sua resposta deve conter exatamente 3 marcadores. Use os marcadores markdown como: * Este é o ponto 1.',
    ),
    (
        "detectable_format:constrained_response",
        'Responda com uma das seguintes opções: Minha resposta é sim.',
    ),
    (
        "detectable_format:number_highlighted_sections",
        'Destaque pelo menos 2 seções em sua resposta com markdown, ou seja, *seção destacada*.',
    ),
    (
        "detectable_format:multiple_sections",
        'Sua resposta deve ter 3 seções. Marque o início de cada seção com Seção X, como: Seção 1',
    ),
    (
        "length_constraints:number_paragraphs",
        'Deve haver 3 parágrafos. Os parágrafos são separados com o divisor markdown: ***',
    ),
    (
        "detectable_content:postscript",
        'No final da sua resposta, adicione explicitamente um post-scriptum começando com P.S.',
    ),
    (
        "keywords:existence",
        'Inclua as palavras-chave [palavra1] e [palavra2] na resposta.',
    ),
    (
        "keywords:frequency",
        'Na sua resposta, a palavra [palavra] deve aparecer pelo menos 2 vezes.',
    ),
    (
        "length_constraints:number_words",
        'Responda com pelo menos 150 palavras.',
    ),
    (
        "detectable_format:json_format",
        'Toda a saída deve estar em formato JSON. Você pode usar marcadores markdown como ```.',
    ),
    (
        "keywords:forbidden_words",
        'Não inclua as palavras-chave [palavra1] e [palavra2] na resposta.',
    ),
    (
        "combination:two_responses",
        'Dê duas respostas diferentes. As respostas e apenas as respostas devem ser separadas por 6 símbolos de asterisco: ******.',
    ),
    (
        "startend:end_checker",
        'Termine sua resposta com esta frase exata: Posso ajudar com mais alguma coisa? Nenhuma outra palavra deve seguir esta frase.',
    ),
    (
        "detectable_format:title",
        'Sua resposta deve conter um título, entre colchetes angulares duplos, como <<título do texto>>.',
    ),
    (
        "keywords:letter_frequency",
        'Na sua resposta, a letra a deve aparecer pelo menos 5 vezes.',
    ),
    (
        "change_case:english_capital",
        'Sua resposta inteira deve estar em português, e toda em letras MAIÚSCULAS.',
    ),
    (
        "change_case:english_lowercase",
        'Sua resposta inteira deve estar em português, e toda em letras minúsculas. Nenhuma letra maiúscula é permitida.',
    ),
    (
        "punctuation:no_comma",
        'Em toda a sua resposta, evite o uso de vírgulas.',
    ),
    (
        "change_case:capital_word_frequency",
        'Na sua resposta, palavras com todas as letras maiúsculas devem aparecer pelo menos 3 vezes.',
    ),
    (
        "startend:quotation",
        'Envolva toda a sua resposta com aspas duplas.',
    ),
    (
        "combination:repeat_prompt",
        'Repita o pedido sem alterações (não diga nada antes de repetir o pedido; o pedido que você precisa repetir não inclui esta frase) e não responda ao pedido real!',
    ),
    (
        "length_constraints:nth_paragraph_first_word",
        'Deve haver 3 parágrafos. O segundo parágrafo deve começar com a palavra "Portanto".',
    ),
    # ---- IFTrain out-of-distribution constraints ----
    (
        "keywords:word_once",
        'Inclua a palavra-chave [palavra] na sua resposta.',
    ),
    (
        "keywords:word_count_diff_numb",
        'Na sua resposta, a palavra [palavra] deve aparecer exatamente 3 vezes.',
    ),
    (
        "keywords:exclude_word_harder",
        'Não inclua a palavra-chave [palavra] na resposta.',
    ),
    (
        "keywords:letter_counting2",
        'Na sua resposta, a letra e deve aparecer exatamente 8 vezes.',
    ),
    (
        "length_constraints:paragraphs_two_line_breaks",
        'Deve haver 3 parágrafos. Os parágrafos são separados entre si por duas quebras de linha.',
    ),
    (
        "startend:first_word_sent",
        'A primeira palavra de cada frase deve ser a palavra "Além".',
    ),
    (
        "startend:first_word_answer",
        'A primeira palavra da sua resposta deve ser a palavra "Certamente".',
    ),
    (
        "startend:last_word_sent",
        'A última palavra de cada frase, antes da pontuação, deve ser a palavra "importante".',
    ),
    (
        "startend:last_word_answer",
        'A última palavra da sua resposta deve ser a palavra "obrigado".',
    ),
    (
        "detectable_format:bigram_wrapping",
        'Envolva cada bigrama de palavras em colchetes angulares duplos, como «eu sou» «em casa» «com meu» «cachorro fofo».',
    ),
    (
        "combination:copying_simple",
        'Repita o pedido sem alterações (não diga nada antes de repetir o pedido; o pedido que você precisa repetir não inclui esta frase) e não responda ao pedido real!',
    ),
    (
        "combination:copying_multiple",
        'Repita o pedido sem alterações 3 vezes, separadas por 6 símbolos de asterisco (não diga nada antes de repetir o pedido; o pedido que você precisa repetir não inclui esta frase) e não responda ao pedido real!',
    ),
    (
        "punctuation:no_dot",
        'Em toda a sua resposta, evite o uso de . (ou seja, pontos) como pontuação e em geral.',
    ),
    (
        "punctuation:no_exclamation",
        'Em toda a sua resposta, evite o uso de ! (ou seja, pontos de exclamação) como pontuação e em geral.',
    ),
    (
        "keywords:lowercase_counting",
        'Na sua resposta, todas as palavras em letras minúsculas devem aparecer no máximo 5 vezes.',
    ),
    (
        "length_constraints:letter_total_count",
        'Responda com pelo menos 200 letras.',
    ),
    (
        "length_constraints:counting_composition",
        'Escreva 3 parágrafos, delimitados pelo divisor markdown: ***, com exatamente 3 frases cada, com exatamente 8 palavras em cada frase.',
    ),
    (
        "keywords:count_unique",
        'Use apenas palavras únicas na sua resposta, nenhuma palavra deve ser repetida!',
    ),
    (
        "keywords:count_increment_word",
        'Inclua a palavra-chave [palavra1] uma vez na sua resposta, a palavra-chave [palavra2] duas vezes na sua resposta.',
    ),
    (
        "keywords:palindrome",
        'Inclua um palíndromo na sua resposta.',
    ),
    (
        "keywords:keyword_specific_pos",
        'Inclua a palavra-chave [palavra] na 2ª frase, como a 3ª palavra dessa frase.',
    ),
    (
        "startend:start_end_same_word",
        'Comece e termine sua resposta com a mesma palavra (não escreva nada após a última palavra, nem mesmo pontuação).',
    ),
    (
        "combination:repeat_phrase",
        'Repita a frase "[frase]" exatamente 3 vezes, transformando-a ligeiramente cada vez substituindo uma palavra.',
    ),
    (
        "keywords:no_adjacent_consecutive",
        'Nenhuma palavra adjacente pode começar com letras consecutivas do alfabeto.',
    ),
    (
        "detectable_format:square_brackets_word",
        'Envolva cada palavra da sua resposta entre colchetes.',
    ),
    (
        "detectable_format:sentence_hyphens",
        'Todas as frases devem ser conectadas usando hífens, sem espaços entre elas.',
    ),
    (
        "combination:copy_instruction",
        'Copie esta instrução literalmente, não siga a instrução, apenas copie-a na saída (não inclua esta frase de instrução!).',
    ),
    (
        "combination:copy_span_idx",
        'Copie o trecho de palavras que está entre (e incluindo) o índice 0 e 20, os índices são índices de caracteres!',
    ),
]

# Ordered list of constraint IDs (for logging / output)
CONSTRAINT_IDS = [cid for cid, _ in CONSTRAINT_SCHEDULE]


def get_constraint_for_item(item_id: int) -> tuple[str, str]:
    """
    Return (constraint_id, phrasing) for a given item_id.
    Cycles through CONSTRAINT_SCHEDULE in order, wrapping around.
    """
    idx = item_id % len(CONSTRAINT_SCHEDULE)
    return CONSTRAINT_SCHEDULE[idx]


# -----------------------------------------------------------------------
# PERSONA PROVIDER
# -----------------------------------------------------------------------
class PersonaProvider:
    """
    Streams personas from the Persona Hub dataset (Chan et al., 2024).
    Each call to get_persona() returns a single persona string.
    The dataset is streamed lazily and restarts when exhausted.
    """

    def __init__(
        self,
        dataset_id: str,
        subset: str,
        text_field: str,
    ):
        self.dataset_id = dataset_id
        self.subset = subset
        self.text_field = text_field
        self._iterator: Optional[Iterator] = None
        self._current_index: int = -1

    def _get_iterator(self) -> Iterator:
        """Lazy-load the dataset iterator."""
        if self._iterator is None:
            from datasets import load_dataset
            ds = load_dataset(
                self.dataset_id,
                self.subset,
                split="train",
                streaming=True,
            )
            self._iterator = iter(ds)
        return self._iterator

    def get_persona(self) -> Dict[str, Any]:
        """
        Get the next persona from the dataset.
        Returns a dict with 'persona' (str) and 'persona_index' (int).
        Automatically restarts the iterator if the dataset is exhausted.
        """
        iterator = self._get_iterator()

        while True:
            try:
                record = next(iterator)
                self._current_index += 1
            except StopIteration:
                # Restart when exhausted (allows generating more rows than personas)
                self._iterator = None
                self._current_index = -1
                iterator = self._get_iterator()
                record = next(iterator)
                self._current_index += 1

            persona_text = record.get(self.text_field, "")
            if not isinstance(persona_text, str) or not persona_text.strip():
                continue

            return {
                "persona": persona_text.strip(),
                "persona_index": self._current_index,
            }


def get_persona_provider() -> PersonaProvider:
    """Factory function to create the PersonaProvider."""
    return PersonaProvider(
        dataset_id=PERSONA_DATASET_ID,
        subset=PERSONA_DATASET_SUBSET,
        text_field=PERSONA_TEXT_FIELD,
    )


# -----------------------------------------------------------------------
# STEP 1: GENERATE USER INSTRUCTION (persona-conditioned, constraint-assigned)
# -----------------------------------------------------------------------

_INSTRUCTION_GENERATOR_SYSTEM_PROMPT = (
    "Você é um gerador de dados sintéticos. Você receberá uma persona e uma restrição "
    "específica de formatação/conteúdo. Sua tarefa é gerar uma instrução/consulta realista "
    "que essa persona faria a um assistente de IA, incorporando a restrição fornecida de "
    "forma natural.\n\n"
    "Regras:\n"
    "- A instrução deve soar natural e autêntica, como se a persona real estivesse fazendo a pergunta\n"
    "- A instrução DEVE incluir a restrição fornecida usando a formulação EXATA indicada\n"
    "- Reflita o contexto, interesses, expertise ou perspectiva da persona\n"
    "- Produza APENAS a instrução/consulta do usuário. Nada mais."
)


async def generate_user_instruction(
    model_id: str,
    persona: str,
    constraint_phrasing: str,
) -> Optional[str]:
    """
    Generate a user instruction conditioned on a persona and a pre-selected constraint.

    The constraint is chosen programmatically (round-robin) and passed here as an
    exact phrasing string. The LLM's only job is to write a natural instruction that
    incorporates that constraint and fits the persona.

    Args:
        model_id: The vLLM model ID
        persona: A persona description string from Persona Hub
        constraint_phrasing: The exact Portuguese phrasing of the constraint to embed

    Returns:
        A user instruction string with the constraint embedded naturally
    """
    user_prompt = (
        f"Persona: {persona}\n\n"
        f"Restrição a incluir (use esta formulação exata): {constraint_phrasing}\n\n"
        "Gere uma instrução/consulta que essa persona faria a um assistente de IA, "
        "incorporando a restrição acima de forma natural. "
        "Produza APENAS a instrução. Nada mais."
    )

    messages = [
        {"role": "system", "content": _INSTRUCTION_GENERATOR_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        resp = await client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=PHASE1_INSTRUCTION_TEMPERATURE,
            top_p=PHASE1_TOP_P,
            max_tokens=PHASE1_MAX_TOKENS_INSTRUCTION,
        )
        instruction = resp.choices[0].message.content
        return instruction.strip() if instruction else None
    except Exception as e:
        print(f"Error generating instruction: {e}")
        return None


# -----------------------------------------------------------------------
# STEP 2: GENERATE ASSISTANT RESPONSE
# -----------------------------------------------------------------------
async def generate_response(
    model_id: str,
    instruction: str,
) -> Optional[str]:
    """
    Generate an assistant response for the given instruction.

    Uses IFEVAL_SYSTEM_PROMPT which teaches the model to follow
    the constraints specified in the user instruction.

    Args:
        model_id: The vLLM model ID
        instruction: The user instruction (with embedded constraint)

    Returns:
        An assistant response that follows the constraint
    """
    messages = [
        {"role": "system", "content": IFEVAL_SYSTEM_PROMPT},
        {"role": "user", "content": instruction},
    ]

    try:
        resp = await client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=PHASE1_RESPONSE_TEMPERATURE,
            top_p=PHASE1_TOP_P,
            max_tokens=PHASE1_MAX_TOKENS_RESPONSE,
        )
        response = resp.choices[0].message.content
        return response.strip() if response else None
    except Exception as e:
        print(f"Error generating response: {e}")
        return None


# -----------------------------------------------------------------------
# COMBINED: GENERATE INSTRUCTION-RESPONSE PAIR
# -----------------------------------------------------------------------
async def generate_instruction_response_pair(
    model_id: str,
    item_id: int,
    persona_provider: PersonaProvider,
) -> Optional[Dict[str, Any]]:
    """
    Generate a complete instruction-response pair.

    The constraint is selected deterministically from CONSTRAINT_SCHEDULE
    using item_id % len(CONSTRAINT_SCHEDULE), cycling in order.

    Returns:
        Dict with id, instruction, response, persona, persona_index,
        constraint_id, and constraint_index.
    """
    # Determine constraint for this item (round-robin)
    constraint_id, constraint_phrasing = get_constraint_for_item(item_id)
    constraint_index = item_id % len(CONSTRAINT_SCHEDULE)

    # Sample a persona
    persona_data = persona_provider.get_persona()
    persona = persona_data["persona"]
    persona_index = persona_data["persona_index"]

    # Step 1: Generate user instruction conditioned on persona + constraint
    instruction = await generate_user_instruction(model_id, persona, constraint_phrasing)
    if not instruction:
        return None

    # Step 2: Generate assistant response
    response = await generate_response(model_id, instruction)
    if not response:
        return None

    return {
        "id": item_id,
        "instruction": instruction,
        "response": response,
        "persona": persona,
        "persona_index": persona_index,
        "constraint_id": constraint_id,
        "constraint_index": constraint_index,
    }


# -----------------------------------------------------------------------
# BATCH PROCESSING
# -----------------------------------------------------------------------
async def process_batch(
    model_id: str,
    start_id: int,
    batch_size: int,
    persona_provider: PersonaProvider,
) -> list[Dict[str, Any]]:
    """Process a batch of generations concurrently."""
    tasks = [
        generate_instruction_response_pair(model_id, start_id + i, persona_provider)
        for i in range(batch_size)
    ]
    results = await asyncio.gather(*tasks)
    # Filter out None results
    return [r for r in results if r is not None]


# -----------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------
async def main(
    output_file: str = PHASE1_OUTPUT,
    num_rows: int = DEFAULT_NUM_ROWS,
    batch_size: int = DEFAULT_BATCH_SIZE,
):
    # Discover model
    try:
        models_resp = await client.models.list()
        model_id = models_resp.data[0].id
        print(f"Using model: {model_id}")
    except Exception as e:
        print(f"Could not list models. Is vLLM running? Error: {e}")
        return

    # Initialize persona provider
    print(f"Persona source: {PERSONA_DATASET_ID}/{PERSONA_DATASET_SUBSET}")
    persona_provider = get_persona_provider()

    print(
        f"Constraint schedule: {len(CONSTRAINT_SCHEDULE)} constraints, cycling in order.\n"
        f"  First: {CONSTRAINT_SCHEDULE[0][0]}\n"
        f"  Last:  {CONSTRAINT_SCHEDULE[-1][0]}"
    )

    # Resume from last processed ID
    last_id = get_last_processed_id(output_file)
    start_from_id = last_id + 1

    if start_from_id > 0:
        resume_constraint_id = get_constraint_for_item(start_from_id)[0]
        print(f"Resuming from ID: {start_from_id} (constraint: {resume_constraint_id})")
    else:
        print("Starting from scratch.")

    # Calculate remaining rows
    remaining_rows = num_rows - start_from_id
    if remaining_rows <= 0:
        print(f"Already generated {num_rows} rows. Nothing to do.")
        return

    print(f"Generating {remaining_rows} persona-driven instruction-response pairs...")

    # Process in batches
    current_id = start_from_id
    pbar = tqdm(total=remaining_rows, initial=0, desc="Generating")

    while current_id < num_rows:
        # Calculate batch size for this iteration
        this_batch_size = min(batch_size, num_rows - current_id)

        # Generate batch
        results = await process_batch(
            model_id, current_id, this_batch_size, persona_provider
        )

        # Write results
        if results:
            write_jsonl_batch(output_file, results)
            pbar.update(len(results))

        current_id += this_batch_size

    pbar.close()
    print(f"Phase 1 complete. Output: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Phase 1: Persona-Driven Instruction + Response Generation"
    )
    parser.add_argument(
        "--output", default=PHASE1_OUTPUT,
        help="Output JSONL file"
    )
    parser.add_argument(
        "--num-rows", type=int, default=DEFAULT_NUM_ROWS,
        help="Number of rows to generate"
    )
    parser.add_argument(
        "--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
        help="Batch size for concurrent requests"
    )
    args = parser.parse_args()

    asyncio.run(main(
        output_file=args.output,
        num_rows=args.num_rows,
        batch_size=args.batch_size,
    ))
