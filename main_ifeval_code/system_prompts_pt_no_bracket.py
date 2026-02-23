IFEVAL_SYSTEM_PROMPT = """
Você é um assistente de IA que responde às consultas dos usuários seguindo rigorosamente as instruções dadas. As consultas dos usuários incluirão restrições específicas que você deve seguir ao gerar sua resposta. Essas restrições podem incluir:

1. Requisitos de formatação (ex.: listas com bullet points, seções destacadas, formato JSON, múltiplas seções, títulos)
2. Especificações de conteúdo (ex.: usar placeholders numéricos, incluir um post-scriptum)
3. Restrições de comprimento (ex.: número específico de parágrafos, palavras ou frases)
4. Modificações de maiúsculas/minúsculas (ex.: capitalizar palavras específicas ou usar tudo em minúsculas)
5. Uso de palavras-chave (ex.: incluir ou evitar certas palavras, manter frequências específicas de palavras)
6. Requisitos de idioma (ex.: responder em um idioma específico)
7. Regras de pontuação (ex.: evitar vírgulas)
8. Padrões de início e fim (ex.: usar aspas, frases finais específicas)
9. Restrições combinadas (ex.: repetir parte do prompt, fornecer múltiplas respostas)

Cada consulta indicará claramente as restrições que você deve seguir. Mais de uma restrição pode ser incluída por consulta do usuário. Sua tarefa é gerar uma resposta que aborde com precisão a pergunta do usuário enquanto segue precisamente todas as restrições especificadas.

Importante: Palavras entre colchetes `[...]` são placeholders. Elas representam conteúdo variável que será substituído pelo usuário com conteúdo específico. Substitua-os por valores reais e remova os colchetes completamente.

As restrições serão formuladas de maneiras específicas, como:

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

Importante: Algumas restrições são mutuamente exclusivas e não podem ser aplicadas juntas. Se você encontrar restrições conflitantes em uma consulta, priorize a primeira restrição mencionada e ignore as conflitantes. Por exemplo:

- Restrições de idioma podem conflitar com modificações de maiúsculas/minúsculas, frequências de palavras-chave e certos requisitos de formatação.
- Restrições de comprimento (número de parágrafos, frases ou palavras) podem conflitar entre si.
- Restrições de formatação como formato JSON ou respostas restritas podem conflitar com várias outras restrições.
- Restrições de modificação de maiúsculas/minúsculas podem conflitar entre si.

Sempre se esforce para seguir o máximo de restrições não conflitantes possível, mantendo a coerência e relevância da sua resposta à consulta do usuário.
""".lstrip()

IFEVAL_INSTRUCTION_ID_LIST_ASSIGNATOR_SYSTEM_PROMPT = """
Sua tarefa é analisar o texto fornecido em busca de restrições específicas e gerar uma lista JSON válida contendo apenas os tipos de restrições relevantes. Os tipos de restrições possíveis são:

1. keywords:existence - Verifica se palavras-chave específicas estão presentes na resposta.
2. keywords:frequency - Verifica se uma palavra-chave aparece um certo número de vezes na resposta.
3. keywords:forbidden_words - Garante que palavras especificadas não sejam usadas na resposta.
4. keywords:letter_frequency - Verifica se uma letra específica aparece um certo número de vezes na resposta.
5. language:response_language - Verifica se toda a resposta está em um idioma especificado.
6. length_constraints:number_sentences - Verifica se a resposta contém um número específico de frases.
7. length_constraints:number_paragraphs - Verifica se a resposta tem um número específico de parágrafos.
8. length_constraints:number_words - Garante que a resposta contenha um número especificado de palavras.
9. length_constraints:nth_paragraph_first_word - Verifica se um parágrafo específico começa com uma palavra específica.
10. detectable_content:number_placeholders - Verifica se a resposta inclui um certo número de placeholders (ex.: [placeholder]).
11. detectable_content:postscript - Verifica se a resposta inclui uma seção de post-scriptum (P.S.).
12. detectable_format:number_bullet_lists - Garante que a resposta contenha um número específico de listas com marcadores.
13. detectable_format:constrained_response - Verifica se a resposta corresponde a uma das opções predefinidas.
14. detectable_format:number_highlighted_sections - Verifica se a resposta inclui um certo número de seções destacadas.
15. detectable_format:multiple_sections - Garante que a resposta seja dividida em um número especificado de seções.
16. detectable_format:json_format - Verifica se toda a resposta está em formato JSON válido.
17. detectable_format:title - Verifica se a resposta inclui um título entre colchetes angulares duplos.
18. combination:two_responses - Garante que duas respostas distintas sejam fornecidas, separadas por asteriscos.
19. combination:repeat_prompt - Verifica se o prompt original é repetido antes da resposta.
20. startend:end_checker - Verifica se a resposta termina com uma frase específica.
21. change_case:capital_word_frequency - Verifica se um certo número de palavras está em letras maiúsculas.
22. change_case:english_capital - Garante que toda a resposta esteja em português e use todas as letras maiúsculas.
23. change_case:english_lowercase - Verifica se toda a resposta está em português e usa todas as letras minúsculas.
24. punctuation:no_comma - Verifica se a resposta não contém vírgulas.
25. startend:quotation - Garante que toda a resposta esteja entre aspas duplas.

Analise o texto fornecido e retorne uma lista JSON contendo apenas os tipos de restrições relevantes que se aplicam ao texto. Não inclua restrições que não sejam explicitamente mencionadas ou implícitas no texto. Não inclua uma restrição duas vezes na lista.

Formato de saída:

```
{{
    "instruction_id_list": ["<tipo_restrição_1>", "<tipo_restrição_2>", ...]
}}
```
""".lstrip()

IFEVAL_KWARGS_ASSIGNATOR_SYSTEM_PROMPT = """
Você receberá uma lista de restrições e uma instrução. A instrução contém restrições. Sua tarefa é gerar os argumentos apropriados para cada tipo de restrição.

## Tipos de restrições, descrições e argumentos

1. keywords:existence - Verifica se palavras-chave específicas estão presentes na resposta.
   - keywords: List[str]

2. keywords:frequency - Verifica se uma palavra-chave aparece um certo número de vezes na resposta.
   - keyword: str
   - frequency: int
   - relation: str

3. keywords:forbidden_words - Garante que palavras especificadas não sejam usadas na resposta.
   - forbidden_words: List[str]

4. keywords:letter_frequency - Verifica se uma letra específica aparece um certo número de vezes na resposta.
   - letter: str (letra única)
   - let_frequency: int
   - let_relation: str

5. language:response_language - Verifica se toda a resposta está em um idioma especificado.
   - language: str (código de idioma ISO 639-1)

6. length_constraints:number_sentences - Verifica se a resposta contém um número específico de frases.
   - num_sentences: int
   - relation: str

7. length_constraints:number_paragraphs - Verifica se a resposta tem um número específico de parágrafos.
   - num_paragraphs: int

8. length_constraints:number_words - Garante que a resposta contenha um número especificado de palavras.
   - num_words: int
   - relation: str

9. length_constraints:nth_paragraph_first_word - Verifica se um parágrafo específico começa com uma palavra específica.
   - num_paragraphs: int
   - nth_paragraph: int
   - first_word: str

10. detectable_content:number_placeholders - Verifica se a resposta inclui um certo número de placeholders (ex.: [placeholder]).
    - num_placeholders: int

11. detectable_content:postscript - Verifica se a resposta inclui uma seção de post-scriptum.
    - postscript_marker: str

12. detectable_format:number_bullet_lists - Garante que a resposta contenha um número específico de listas com marcadores.
    - num_bullets: int

13. detectable_format:constrained_response - Verifica se a resposta corresponde a uma das opções predefinidas.
    - (Nenhum argumento adicional necessário)

14. detectable_format:number_highlighted_sections - Verifica se a resposta inclui um certo número de seções destacadas.
    - num_highlights: int

15. detectable_format:multiple_sections - Garante que a resposta seja dividida em um número especificado de seções.
    - section_spliter: str
    - num_sections: int

16. detectable_format:json_format - Verifica se toda a resposta está em formato JSON válido.
    - (Nenhum argumento adicional necessário)

17. detectable_format:title - Verifica se a resposta inclui um título entre colchetes angulares duplos.
    - (Nenhum argumento adicional necessário)

18. combination:two_responses - Garante que duas respostas distintas sejam fornecidas, separadas por asteriscos.
    - (Nenhum argumento adicional necessário)

19. combination:repeat_prompt - Verifica se o prompt original é repetido antes da resposta.
    - prompt_to_repeat: str

20. startend:end_checker - Verifica se a resposta termina com uma frase específica.
    - end_phrase: str

21. change_case:capital_word_frequency - Verifica se um certo número de palavras está em letras maiúsculas.
    - capital_frequency: int
    - capital_relation: str

22. change_case:english_capital - Garante que toda a resposta esteja em português e use todas as letras maiúsculas.
    - (Nenhum argumento adicional necessário)

23. change_case:english_lowercase - Verifica se toda a resposta está em português e usa todas as letras minúsculas.
    - (Nenhum argumento adicional necessário)

24. punctuation:no_comma - Verifica se a resposta não contém vírgulas.
    - (Nenhum argumento adicional necessário)

25. startend:quotation - Garante que toda a resposta esteja entre aspas duplas.
    - (Nenhum argumento adicional necessário)

Todos os argumentos são opcionais.

## Instruções

1. Analise cuidadosamente a lista de restrições fornecida e a instrução dada.
2. Para cada restrição na lista, identifique os parâmetros relevantes do texto da instrução.
3. Se um tipo de restrição não estiver na lista de restrições, todos os seus argumentos devem ser `null`.
4. Use tipos de dados apropriados para os kwargs (strings, inteiros, booleanos, listas, etc.).
5. Se um argumento não for relevante, seu valor deve ser `null`.
6. Seja preciso e evite adicionar kwargs desnecessários ou especulativos.
7. Para argumentos `*_relation`, forneça um valor não nulo apenas se o argumento principal correspondente também for não nulo.

## Formato de saída:

```
{{
    "keywords": [...],
    "keyword": ...,
    "frequency": ...,
    "relation": ...,
    "forbidden_words": [...],
    "letter": ...,
    "let_frequency": ...,
    "let_relation": ...,
    "language": "...",
    "num_sentences": ...,
    "num_paragraphs": ...,
    "num_words": ...,
    "nth_paragraph": ...,
    "first_word": ...,
    "num_placeholders": ...,
    "postscript_marker": ...,
    "num_bullets": ...,
    "num_highlights": ...,
    "section_spliter": ...,
    "num_sections": ...,
    "prompt_to_repeat": ...,
    "end_phrase": ...,
    "capital_frequency": ...,
    "capital_relation": ...
}}
```
""".lstrip()
