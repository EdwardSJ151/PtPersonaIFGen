IFEVAL_RESPONSE_VERIFICATION_FUNCTION_ARGUMENTS_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "language": {
            "type": ["string", "null"],
        },
        "num_sentences": {
            "type": ["integer", "null"],
            "minimum": 1,
        },
        "relation": {
            "type": ["string", "null"],
            "enum": ["less than", "at least", "menos de", "pelo menos"],
        },
        "num_placeholders": {
            "type": ["integer", "null"],
            "minimum": 1,
        },
        "num_bullets": {
            "type": ["integer", "null"],
            "minimum": 1,
        },
        "starter": {
            "type": ["string", "null"],
        },
        "num_highlights": {
            "type": ["integer", "null"],
            "minimum": 1,
        },
        "section_spliter": {
            "type": ["string", "null"],
            "enum": ["Section", "SECTION", "Seção", "SEÇÃO"],
        },
        "num_sections": {
            "type": ["integer", "null"],
            "minimum": 1,
        },
        "num_paragraphs": {
            "type": ["integer", "null"],
            "minimum": 1,
        },
        "postscript_marker": {
            "type": ["string", "null"],
            "enum": ["P.S.", "P.P.S"],
        },
        "original_message": {
            "type": ["string", "null"],
        },
        "keywords": {
            "type": "array",
            "items": {"type": "string"},
        },
        "keyword": {
            "type": ["string", "null"],
        },
        "frequency": {
            "type": ["integer", "null"],
            "minimum": 1,
        },
        "num_words": {
            "type": ["integer", "null"],
            "minimum": 1,
        },
        "nth_paragraph": {
            "type": ["integer", "null"],
            "minimum": 1,
        },
        "first_word": {
            "type": ["string", "null"],
        },
        "key_sentences": {
            "type": ["array", "null"],
            "items": {"type": "string"},
        },
        "forbidden_words": {
            "type": ["array", "null"],
            "items": {"type": "string"},
        },
        "original_paragraph": {
            "type": ["string", "null"],
        },
        "low": {
            "type": ["integer", "null"],
            "minimum": 0,
        },
        "high": {
            "type": ["integer", "null"],
            "minimum": 0,
        },
        "prompt_to_repeat": {
            "type": ["string", "null"],
        },
        "end_phrase": {
            "type": ["string", "null"],
        },
        "letter": {
            "type": ["string", "null"],
            "minLength": 1,
            "maxLength": 1,
            "pattern": "[a-zA-Z]",
        },
        "let_frequency": {
            "type": ["integer", "null"],
            "minimum": 1,
        },
        "let_relation": {
            "type": ["string", "null"],
            "enum": ["less than", "at least", "menos de", "pelo menos"],
        },
        "capital_frequency": {
            "type": ["integer", "null"],
            "minimum": 1,
        },
        "capital_relation": {
            "type": ["string", "null"],
            "enum": ["less than", "at least", "menos de", "pelo menos"],
        },
        "count": {
            "type": ["integer", "null"],
            "minimum": 1,
        },
        "last_word": {
            "type": ["string", "null"],
        },
        "prompt_to_copy": {
            "type": ["string", "null"],
        },
        "copy_count": {
            "type": ["integer", "null"],
            "minimum": 2,
        },
        "max_count": {
            "type": ["integer", "null"],
            "minimum": 1,
        },
        "num_letters": {
            "type": ["integer", "null"],
            "minimum": 1,
        },
        "n_sent": {
            "type": ["integer", "null"],
            "minimum": 1,
        },
        "n_words": {
            "type": ["integer", "null"],
            "minimum": 1,
        },
        "keyword1": {
            "type": ["string", "null"],
        },
        "keyword2": {
            "type": ["string", "null"],
        },
        "sentence_num": {
            "type": ["integer", "null"],
            "minimum": 1,
        },
        "word_num": {
            "type": ["integer", "null"],
            "minimum": 1,
        },
        "phrase": {
            "type": ["string", "null"],
        },
        "repeat_count": {
            "type": ["integer", "null"],
            "minimum": 2,
        },
        "instruction_to_copy": {
            "type": ["string", "null"],
        },
        "source_text": {
            "type": ["string", "null"],
        },
        "n_start": {
            "type": ["integer", "null"],
            "minimum": 0,
        },
        "n_end": {
            "type": ["integer", "null"],
            "minimum": 0,
        },
    },
    "required": [
        "language",
        "num_sentences",
        "relation",
        "num_placeholders",
        "num_bullets",
        "starter",
        "num_highlights",
        "section_spliter",
        "num_sections",
        "num_paragraphs",
        "postscript_marker",
        "original_message",
        "keywords",
        "keyword",
        "frequency",
        "num_words",
        "nth_paragraph",
        "first_word",
        "key_sentences",
        "forbidden_words",
        "original_paragraph",
        "low",
        "high",
        "prompt_to_repeat",
        "end_phrase",
        "letter",
        "let_frequency",
        "let_relation",
        "capital_frequency",
        "capital_relation",
        "count",
        "last_word",
        "prompt_to_copy",
        "copy_count",
        "max_count",
        "num_letters",
        "n_sent",
        "n_words",
        "keyword1",
        "keyword2",
        "sentence_num",
        "word_num",
        "phrase",
        "repeat_count",
        "instruction_to_copy",
        "source_text",
        "n_start",
        "n_end",
    ],
    "additionalProperties": False,
}

IFEVAL_INSTRUCTION_ID_LIST_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "instruction_id_list": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "keywords:existence",
                    "keywords:frequency",
                    "keywords:forbidden_words",
                    "keywords:letter_frequency",
                    "language:response_language",
                    "length_constraints:number_sentences",
                    "length_constraints:number_paragraphs",
                    "length_constraints:number_words",
                    "length_constraints:nth_paragraph_first_word",
                    "detectable_content:number_placeholders",
                    "detectable_content:postscript",
                    "detectable_format:number_bullet_lists",
                    "detectable_format:constrained_response",
                    "detectable_format:number_highlighted_sections",
                    "detectable_format:multiple_sections",
                    "detectable_format:json_format",
                    "detectable_format:title",
                    "combination:two_responses",
                    "combination:repeat_prompt",
                    "startend:end_checker",
                    "change_case:capital_word_frequency",
                    "change_case:english_capital",
                    "change_case:english_lowercase",
                    "punctuation:no_comma",
                    "startend:quotation",
                    "keywords:word_once",
                    "keywords:word_count_diff_numb",
                    "keywords:exclude_word_harder",
                    "keywords:letter_counting2",
                    "length_constraints:paragraphs_two_line_breaks",
                    "startend:first_word_sent",
                    "startend:first_word_answer",
                    "startend:last_word_sent",
                    "startend:last_word_answer",
                    "detectable_format:bigram_wrapping",
                    "combination:copying_simple",
                    "combination:copying_multiple",
                    "punctuation:no_dot",
                    "punctuation:no_exclamation",
                    "keywords:lowercase_counting",
                    "length_constraints:letter_total_count",
                    "length_constraints:counting_composition",
                    "keywords:count_unique",
                    "keywords:count_increment_word",
                    "keywords:palindrome",
                    "keywords:keyword_specific_pos",
                    "startend:start_end_same_word",
                    "combination:repeat_phrase",
                    "keywords:no_adjacent_consecutive",
                    "detectable_format:square_brackets_word",
                    "detectable_format:sentence_hyphens",
                    "combination:copy_instruction",
                    "combination:copy_span_idx",
                ],
            },
        }
    },
    "required": ["instruction_id_list"],
}
