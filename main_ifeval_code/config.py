"""
Configuração compartilhada e constantes para o pipeline vLLM.
Referencia pipeline/system_prompts_pt.py e pipeline/json_schemas_pt.py
"""

import os

from ifeval_persona.main_ifeval_code.system_prompts_pt import (
    IFEVAL_SYSTEM_PROMPT,
    IFEVAL_INSTRUCTION_ID_LIST_ASSIGNATOR_SYSTEM_PROMPT,
    IFEVAL_KWARGS_ASSIGNATOR_SYSTEM_PROMPT,
)
from ifeval_persona.main_ifeval_code.json_schemas_pt import (
    IFEVAL_INSTRUCTION_ID_LIST_JSON_SCHEMA,
    IFEVAL_RESPONSE_VERIFICATION_FUNCTION_ARGUMENTS_JSON_SCHEMA,
)

# -----------------------------------------------------------------------
# CONFIGURAÇÃO DO SERVIDOR VLLM
# -----------------------------------------------------------------------
VLLM_BASE_URL = os.environ.get("VLLM_BASE_URL", "http://localhost:8021/v1")
VLLM_API_KEY = os.environ.get("VLLM_API_KEY", "no-key-needed")

# -----------------------------------------------------------------------
# CONFIGURAÇÃO DA FONTE DE TÓPICOS
# -----------------------------------------------------------------------
# Toggle: "huggingface" ou "predefined"
TOPIC_SOURCE = os.environ.get("TOPIC_SOURCE", "huggingface")

# Configurações do dataset HuggingFace (quando TOPIC_SOURCE="huggingface")
HF_DATASET_ID = os.environ.get("HF_DATASET_ID", "HuggingFaceFW/finewiki")
HF_DATASET_SUBSET = os.environ.get("HF_DATASET_SUBSET", "pt")
HF_TEXT_FIELD = os.environ.get("HF_TEXT_FIELD", "text")
HF_TITLE_FIELD = os.environ.get("HF_TITLE_FIELD", "title")
HF_MIN_CHARS = int(os.environ.get("HF_MIN_CHARS", "200"))
HF_MAX_CONTEXT_CHARS = int(os.environ.get("HF_MAX_CONTEXT_CHARS", "1500000"))

# Tópicos predefinidos (quando TOPIC_SOURCE="predefined")
PREDEFINED_TOPICS = [
    "culinária e receitas",
    "viagens e turismo",
    "ciência e tecnologia",
    "história e cultura",
    "saúde e fitness",
    "negócios e finanças",
    "educação e aprendizagem",
    "artes e entretenimento",
    "esportes e recreação",
    "natureza e meio ambiente",
    "filosofia e ética",
    "psicologia e autodesenvolvimento",
    "política e atualidades",
    "literatura e escrita",
    "música e artes cênicas",
    "arquitetura e design",
    "astronomia e espaço",
    "matemática e lógica",
    "linguística e idiomas",
    "mitologia e folclore",
    "direito e questões jurídicas",
    "medicina e saúde",
    "economia e mercados",
    "sociologia e sociedade",
    "engenharia e construção",
    "agricultura e pecuária",
    "moda e estilo",
    "jogos e esports",
    "fotografia e artes visuais",
    "relacionamentos e namoro",
]

# -----------------------------------------------------------------------
# PARÂMETROS DE GERAÇÃO (de pipeline/pipeline.py)
# -----------------------------------------------------------------------

# Fase 1: Geração em duas etapas
PHASE1_INSTRUCTION_TEMPERATURE = 1.2  # Maior para instruções diversas
PHASE1_RESPONSE_TEMPERATURE = 0.7     # Menor para respostas precisas
PHASE1_TOP_P = 0.8
PHASE1_MAX_TOKENS_INSTRUCTION = 2048   # Instruções do usuário são mais curtas
PHASE1_MAX_TOKENS_RESPONSE = 2048     # Respostas podem ser mais longas

# Fase 2: Detecção de restrições (linhas 207-209 de pipeline.py)
PHASE2_TEMPERATURE = 0.2
PHASE2_MAX_TOKENS = 1024

# Fase 3: Extração de parâmetros (linhas 229-231 de pipeline.py)
PHASE3_TEMPERATURE = 0.2
PHASE3_MAX_TOKENS = 2048

# -----------------------------------------------------------------------
# CONFIGURAÇÕES DE LOTE
# -----------------------------------------------------------------------
DEFAULT_BATCH_SIZE = 4  # Requisições concorrentes por lote
DEFAULT_NUM_ROWS = 2000000  # Total de linhas a gerar (de pipeline.py linha 194)

# -----------------------------------------------------------------------
# ARQUIVOS DE SAÍDA
# -----------------------------------------------------------------------
PHASE1_OUTPUT = "phase1_generated_output.jsonl"
PHASE2_OUTPUT = "phase2_detection_output.jsonl"
PHASE3_OUTPUT = "phase3_extraction_output.jsonl"
PHASE4_OUTPUT = "phase4_final_output.jsonl"

# -----------------------------------------------------------------------
# PROMPT DO SISTEMA PARA GERAR INSTRUÇÕES DO USUÁRIO
# Este prompt ensina ao modelo as restrições EXATAS do IFEval de IFEVAL_SYSTEM_PROMPT
# Tanto a Etapa 1 (geração de instrução) quanto a Etapa 2 (geração de resposta) usam
# as mesmas definições de restrições exatas para garantir consistência.
# -----------------------------------------------------------------------

# As formulações exatas das restrições que o modelo deve usar ao gerar instruções.
# Estas DEVEM corresponder às formulações em IFEVAL_SYSTEM_PROMPT exatamente.
IFEVAL_CONSTRAINT_PHRASINGS = """
- "Sua resposta INTEIRA deve estar em [idioma], nenhum outro idioma é permitido." ([idioma] pode ser "pt" para português, "en" para inglês, "es" para espanhol, etc., seguindo códigos ISO 639-1)
- "Sua resposta deve conter [relação] [num_frases] frases." ([relação] pode ser "menos de" ou "pelo menos"; [num_frases] pode ser qualquer número até 20)
- "A resposta deve conter pelo menos [num_placeholders] placeholders representados por colchetes, como [endereço]." ([num_placeholders] pode ser qualquer número até 4)
- "Sua resposta deve conter exatamente [num_marcadores] marcadores. Use os marcadores markdown como: * Este é o ponto 1." ([num_marcadores] pode ser qualquer número até 5)
- "Responda com uma das seguintes opções: [opções_resposta]" ([opções_resposta] pode ser "Minha resposta é sim.", "Minha resposta é não.", "Minha resposta é talvez.")
- "Durante a conversa, quando for sua vez, sempre comece com [início]" ([início] pode ser "Eu diria", "Minha resposta é", "Eu acredito", etc.)
- "Destaque pelo menos [num_destaques] seções em sua resposta com markdown, ou seja, *seção destacada*." ([num_destaques] pode ser qualquer número até 4)
- "Sua resposta deve ter [num_seções] seções. Marque o início de cada seção com [divisor_seção] X, como: [divisor_seção] 1" ([num_seções] pode ser qualquer número até 5; [divisor_seção] pode ser "Seção" ou "SEÇÃO")
- "Deve haver [num_parágrafos] parágrafos. Os parágrafos são separados com o divisor markdown: ***" ([num_parágrafos] pode ser qualquer número até 5)
- "No final da sua resposta, adicione explicitamente um post-scriptum começando com [postscript]" ([postscript] pode ser "P.S." ou "P.P.S")
- "Inclua as palavras-chave [palavras_chave] na resposta." ([palavras_chave] pode ser uma lista de palavras-chave geradas)
- "Na sua resposta, a palavra [palavra_chave] deve aparecer [relação] [frequência] vezes." ([palavra_chave] pode ser qualquer palavra; [relação] pode ser "menos de" ou "pelo menos"; [frequência] pode ser qualquer número até 3)
- "Responda com [relação] [num_palavras] palavras." ([relação] pode ser "menos de" ou "pelo menos"; [num_palavras] pode ser qualquer número entre 100 e 500)
- "Toda a saída deve estar em formato JSON. Você pode usar marcadores markdown como ```."
- "Não inclua as palavras-chave [palavras_proibidas] na resposta." ([palavras_proibidas] pode ser uma lista de palavras-chave geradas)
- "Dê duas respostas diferentes. As respostas e apenas as respostas devem ser separadas por 6 símbolos de asterisco: ******."
- "Termine sua resposta com esta frase exata [final]. Nenhuma outra palavra deve seguir esta frase." ([final] pode ser "Alguma outra pergunta?" ou "Posso ajudar com mais alguma coisa?")
- "Sua resposta deve conter um título, entre colchetes angulares duplos, como <<poema de alegria>>."
- "Na sua resposta, a letra [letra] deve aparecer [relação_letra] [frequência_letra] vezes." ([letra] pode ser qualquer letra; [relação_letra] pode ser "menos de" ou "pelo menos"; [frequência_letra] pode ser qualquer número até 10)
- "Sua resposta inteira deve estar em português, e toda em letras MAIÚSCULAS."
- "Sua resposta inteira deve estar em português, e toda em letras minúsculas. Nenhuma letra maiúscula é permitida."
- "Em toda a sua resposta, evite o uso de vírgulas."
- "Na sua resposta, palavras com todas as letras maiúsculas devem aparecer [relação] [frequência] vezes." ([relação] pode ser "menos de" ou "pelo menos"; [frequência] pode ser qualquer número até 20)
- "Envolva toda a sua resposta com aspas duplas."
- "Inclua a palavra-chave [palavra_chave] na sua resposta." ([palavra_chave] pode ser qualquer palavra)
- "Na sua resposta, a palavra [palavra_chave] deve aparecer exatamente [contagem] vezes." ([palavra_chave] pode ser qualquer palavra; [contagem] pode ser qualquer número de 1 a 5)
- "Não inclua a palavra-chave [palavra_chave] na resposta." ([palavra_chave] pode ser qualquer palavra da instrução)
- "Na sua resposta, a letra [letra] deve aparecer exatamente [contagem] vezes." ([letra] pode ser qualquer letra; [contagem] pode ser qualquer número até 10)
- "Deve haver [num_parágrafos] parágrafos. Os parágrafos são separados entre si por duas quebras de linha."
- "A primeira palavra de cada frase deve ser a palavra [primeira_palavra]." ([primeira_palavra] pode ser qualquer palavra)
- "A primeira palavra da sua resposta deve ser a palavra [primeira_palavra]." ([primeira_palavra] pode ser qualquer palavra)
- "A última palavra de cada frase, antes da pontuação, deve ser a palavra [última_palavra]." ([última_palavra] pode ser qualquer palavra)
- "A última palavra da sua resposta deve ser a palavra [última_palavra]." ([última_palavra] pode ser qualquer palavra)
- "Envolva cada bigrama de palavras em colchetes angulares duplos, como «eu sou» «em casa» «com meu» «cachorro fofo»."
- "Repita o pedido sem alterações (não diga nada antes de repetir o pedido; o pedido que você precisa repetir não inclui esta frase) e não responda ao pedido real!"
- "Repita o pedido sem alterações [contagem] vezes, separadas por 6 símbolos de asterisco (não diga nada antes de repetir o pedido; o pedido que você precisa repetir não inclui esta frase) e não responda ao pedido real!" ([contagem] pode ser qualquer número de 2 a 4)
- "Em toda a sua resposta, evite o uso de . (ou seja, pontos) como pontuação e em geral."
- "Em toda a sua resposta, evite o uso de ! (ou seja, pontos de exclamação) como pontuação e em geral."
- "Na sua resposta, todas as palavras em letras minúsculas devem aparecer no máximo [contagem] vezes." ([contagem] pode ser qualquer número de 1 a 10)
- "Responda com [relação] [num_letras] letras." ([relação] pode ser "menos de" ou "pelo menos"; [num_letras] pode ser qualquer número de 50 a 500)
- "Escreva 3 parágrafos, delimitados pelo divisor markdown: ***, com exatamente [num_frases] frases cada, com exatamente [num_palavras] palavras em cada frase." ([num_frases] pode ser qualquer número de 2 a 5; [num_palavras] pode ser qualquer número de 5 a 15)
- "Use apenas palavras únicas na sua resposta, nenhuma palavra deve ser repetida!"
- "Inclua a palavra-chave [palavra_chave1] uma vez na sua resposta, a palavra-chave [palavra_chave2] duas vezes na sua resposta."
- "Inclua um palíndromo na sua resposta."
- "Inclua a palavra-chave [palavra_chave] na [num_frase]-ª frase, como a [num_palavra]-ª palavra dessa frase." ([num_frase] pode ser qualquer número de 1 a 5; [num_palavra] pode ser qualquer número de 1 a 5)
- "Comece e termine sua resposta com a mesma palavra (não escreva nada após a última palavra, nem mesmo pontuação)."
- "Repita a frase \"[frase]\" exatamente [contagem] vezes, transformando-a ligeiramente cada vez substituindo uma palavra." ([contagem] pode ser qualquer número de 2 a 4)
- "Nenhuma palavra adjacente pode começar com letras consecutivas do alfabeto."
- "Envolva cada palavra da sua resposta entre colchetes."
- "Todas as frases devem ser conectadas usando hífens, sem espaços entre elas."
- "Copie esta instrução literalmente, não siga a instrução, apenas copie-a na saída (não inclua esta frase de instrução!)."
- "Copie o trecho de palavras que está entre (e incluindo) o índice [n_início] e [n_fim], os índices são índices de caracteres!" ([n_início] e [n_fim] podem ser qualquer número inteiro não negativo)
""".strip()


USER_INSTRUCTION_GENERATOR_SYSTEM_PROMPT = f"""Você é um gerador de dados sintéticos. Sua tarefa é gerar instruções/consultas realistas de usuários que incluam restrições específicas de formatação ou conteúdo.

As instruções de usuário que você gera devem soar naturais, como se uma pessoa real estivesse pedindo ajuda a um assistente de IA. Cada instrução DEVE incluir uma ou mais restrições usando as formulações EXATAS abaixo.

## IMPORTANTE: Use Estas Formulações Exatas de Restrições

{IFEVAL_CONSTRAINT_PHRASINGS}

## Diretrizes

- Gere instruções que sejam diversas em tópico e tipo de restrição
- Faça as instruções soarem naturais e conversacionais
- Inclua 1-3 restrições por instrução (não sobrecarregue)
- Use as formulações EXATAS das restrições acima (substituindo placeholders como [num_palavras] por valores reais sem colchetes)
- Varie quais restrições você usa em diferentes instruções

## IMPORTANTE: Conflitos de Restrições

Algumas restrições são mutuamente exclusivas e não podem ser aplicadas juntas. NÃO combine restrições conflitantes em uma única instrução:

- Restrições de idioma podem conflitar com modificações de maiúsculas/minúsculas, frequências de palavras-chave e certos requisitos de formatação.
- Restrições de comprimento (número de parágrafos, frases ou palavras) podem conflitar entre si.
- Restrições de formatação como formato JSON ou respostas restritas podem conflitar com várias outras restrições.
- Restrições de modificação de maiúsculas/minúsculas podem conflitar entre si (ex.: não combine "todas letras maiúsculas" com "todas letras minúsculas").

## Formato de Saída

Produza APENAS a instrução/consulta do usuário. Não inclua nenhuma explicação, metadados ou raciocínio.
"""

# -----------------------------------------------------------------------
# RE-EXPORTAR PROMPTS E SCHEMAS
# -----------------------------------------------------------------------
__all__ = [
    # Prompts
    "IFEVAL_SYSTEM_PROMPT",
    "IFEVAL_INSTRUCTION_ID_LIST_ASSIGNATOR_SYSTEM_PROMPT",
    "IFEVAL_KWARGS_ASSIGNATOR_SYSTEM_PROMPT",
    "IFEVAL_CONSTRAINT_PHRASINGS",
    "USER_INSTRUCTION_GENERATOR_SYSTEM_PROMPT",
    # Schemas
    "IFEVAL_INSTRUCTION_ID_LIST_JSON_SCHEMA",
    "IFEVAL_RESPONSE_VERIFICATION_FUNCTION_ARGUMENTS_JSON_SCHEMA",
    # Config
    "VLLM_BASE_URL",
    "VLLM_API_KEY",
    "TOPIC_SOURCE",
    "HF_DATASET_ID",
    "HF_DATASET_SUBSET",
    "HF_TEXT_FIELD",
    "HF_TITLE_FIELD",
    "HF_MIN_CHARS",
    "HF_MAX_CONTEXT_CHARS",
    "PREDEFINED_TOPICS",
    "PHASE1_INSTRUCTION_TEMPERATURE",
    "PHASE1_RESPONSE_TEMPERATURE",
    "PHASE1_TOP_P",
    "PHASE1_MAX_TOKENS_INSTRUCTION",
    "PHASE1_MAX_TOKENS_RESPONSE",
    "PHASE2_TEMPERATURE",
    "PHASE2_MAX_TOKENS",
    "PHASE3_TEMPERATURE",
    "PHASE3_MAX_TOKENS",
    "DEFAULT_BATCH_SIZE",
    "DEFAULT_NUM_ROWS",
    "PHASE1_OUTPUT",
    "PHASE2_OUTPUT",
    "PHASE3_OUTPUT",
    "PHASE4_OUTPUT",
]
