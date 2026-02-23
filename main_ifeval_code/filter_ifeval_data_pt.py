import json
from typing import TYPE_CHECKING

from datasets import load_dataset
from ifeval_persona.lmeval.utils import process_results

if TYPE_CHECKING:
    from datasets import Dataset


INSTRUCTION_ARGS = {
    "keywords:existence": ["keywords"],
    "keywords:frequency": ["keyword", "frequency", "relation"],
    "keywords:forbidden_words": ["forbidden_words"],
    "keywords:letter_frequency": ["letter", "let_frequency", "let_relation"],
    "language:response_language": ["language"],
    "length_constraints:number_sentences": ["num_sentences", "relation"],
    "length_constraints:number_paragraphs": ["num_paragraphs"],
    "length_constraints:number_words": ["num_words", "relation"],
    "length_constraints:nth_paragraph_first_word": [
        "num_paragraphs",
        "nth_paragraph",
        "first_word",
    ],
    "detectable_content:number_placeholders": ["num_placeholders"],
    "detectable_content:postscript": ["postscript_marker"],
    "detectable_format:number_bullet_lists": ["num_bullets"],
    "detectable_format:constrained_response": [],
    "detectable_format:number_highlighted_sections": ["num_highlights"],
    "detectable_format:multiple_sections": ["section_spliter", "num_sections"],
    "detectable_format:json_format": [],
    "detectable_format:title": [],
    "combination:two_responses": [],
    "combination:repeat_prompt": ["prompt_to_repeat"],
    "startend:end_checker": ["end_phrase"],
    "change_case:capital_word_frequency": ["capital_frequency", "capital_relation"],
    "change_case:english_capital": [],
    "change_case:english_lowercase": [],
    "punctuation:no_comma": [],
    "startend:quotation": [],
    # --- IFTrain out-of-distribution constraints ---
    "keywords:word_once": ["keyword"],
    "keywords:word_count_diff_numb": ["keyword", "count"],
    "keywords:exclude_word_harder": ["keyword"],
    "keywords:letter_counting2": ["letter", "count"],
    "length_constraints:paragraphs_two_line_breaks": ["num_paragraphs"],
    "startend:first_word_sent": ["first_word"],
    "startend:first_word_answer": ["first_word"],
    "startend:last_word_sent": ["last_word"],
    "startend:last_word_answer": ["last_word"],
    "detectable_format:bigram_wrapping": [],
    "combination:copying_simple": ["prompt_to_copy"],
    "combination:copying_multiple": ["prompt_to_copy", "copy_count"],
    "punctuation:no_dot": [],
    "punctuation:no_exclamation": [],
    "keywords:lowercase_counting": ["max_count"],
    "length_constraints:letter_total_count": ["num_letters", "relation"],
    "length_constraints:counting_composition": ["n_sent", "n_words"],
    "keywords:count_unique": [],
    "keywords:count_increment_word": ["keyword1", "keyword2"],
    "keywords:palindrome": [],
    "keywords:keyword_specific_pos": ["keyword", "sentence_num", "word_num"],
    "startend:start_end_same_word": [],
    "combination:repeat_phrase": ["phrase", "repeat_count"],
    "keywords:no_adjacent_consecutive": [],
    "detectable_format:square_brackets_word": [],
    "detectable_format:sentence_hyphens": [],
    "combination:copy_instruction": ["instruction_to_copy"],
    "combination:copy_span_idx": ["source_text", "n_start", "n_end"],
}

ALL_ARGUMENTS = {
    "keywords",
    "keyword",
    "frequency",
    "relation",
    "forbidden_words",
    "letter",
    "let_frequency",
    "let_relation",
    "language",
    "num_sentences",
    "num_paragraphs",
    "num_words",
    "nth_paragraph",
    "first_word",
    "num_placeholders",
    "postscript_marker",
    "num_bullets",
    "num_highlights",
    "section_spliter",
    "num_sections",
    "prompt_to_repeat",
    "end_phrase",
    "capital_frequency",
    "capital_relation",
    # --- IFTrain out-of-distribution arguments ---
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
}

IFEVAL_INSTRUCTION_CONFLICTS = {
    "keywords:existence": {"keywords:existence"},
    "keywords:frequency": {"keywords:frequency"},
    "keywords:forbidden_words": {"keywords:forbidden_words"},
    "keywords:letter_frequency": {"keywords:letter_frequency"},
    "language:response_language": {
        "change_case:english_capital",
        "change_case:english_lowercase",
        "startend:end_checker",
        "keywords:frequency",
        "keywords:forbidden_words",
        "detectable_format:multiple_sections",
        "keywords:existence",
        "language:response_language",
    },
    "length_constraints:number_sentences": {"length_constraints:number_sentences"},
    "length_constraints:number_paragraphs": {
        "length_constraints:number_sentences",
        "length_constraints:nth_paragraph_first_word",
        "length_constraints:number_paragraphs",
    },
    "length_constraints:number_words": {"length_constraints:number_words"},
    "length_constraints:nth_paragraph_first_word": {
        "length_constraints:nth_paragraph_first_word",
        "length_constraints:number_paragraphs",
    },
    "detectable_content:number_placeholders": {
        "detectable_content:number_placeholders"
    },
    "detectable_content:postscript": {"detectable_content:postscript"},
    "detectable_format:number_bullet_lists": {"detectable_format:number_bullet_lists"},
    "detectable_format:constrained_response": {
        "startend:quotation",
        "length_constraints:number_words",
        "detectable_format:constrained_response",
        "change_case:english_capital",
        "startend:end_checker",
        "keywords:forbidden_words",
        "length_constraints:number_sentences",
        "combination:repeat_prompt",
        "combination:two_responses",
        "punctuation:no_comma",
        "detectable_format:number_highlighted_sections",
        "change_case:english_lowercase",
        "detectable_format:number_bullet_lists",
        "detectable_content:number_placeholders",
        "keywords:letter_frequency",
        "keywords:frequency",
        "length_constraints:number_paragraphs",
        "keywords:existence",
        "length_constraints:nth_paragraph_first_word",
        "detectable_format:title",
        "change_case:capital_word_frequency",
        "detectable_format:json_format",
        "detectable_format:multiple_sections",
        "detectable_content:postscript",
        "language:response_language",
    },
    "detectable_format:number_highlighted_sections": {
        "detectable_format:number_highlighted_sections"
    },
    "detectable_format:multiple_sections": {
        "detectable_format:multiple_sections",
        "detectable_format:number_highlighted_sections",
        "language:response_language",
    },
    "detectable_format:json_format": {
        "startend:quotation",
        "length_constraints:number_words",
        "detectable_format:constrained_response",
        "change_case:english_capital",
        "detectable_format:number_bullet_lists",
        "detectable_content:number_placeholders",
        "startend:end_checker",
        "keywords:letter_frequency",
        "keywords:frequency",
        "length_constraints:number_paragraphs",
        "length_constraints:nth_paragraph_first_word",
        "length_constraints:number_sentences",
        "language:response_language",
        "combination:repeat_prompt",
        "detectable_format:title",
        "change_case:capital_word_frequency",
        "combination:two_responses",
        "detectable_format:json_format",
        "punctuation:no_comma",
        "detectable_format:number_highlighted_sections",
        "detectable_format:multiple_sections",
        "detectable_content:postscript",
        "change_case:english_lowercase",
    },
    "detectable_format:title": {"detectable_format:title"},
    "combination:two_responses": {
        "startend:quotation",
        "length_constraints:number_words",
        "detectable_format:constrained_response",
        "change_case:english_capital",
        "detectable_format:number_bullet_lists",
        "detectable_content:number_placeholders",
        "startend:end_checker",
        "keywords:letter_frequency",
        "keywords:frequency",
        "length_constraints:number_paragraphs",
        "length_constraints:nth_paragraph_first_word",
        "length_constraints:number_sentences",
        "combination:repeat_prompt",
        "change_case:capital_word_frequency",
        "combination:two_responses",
        "detectable_format:json_format",
        "detectable_format:number_highlighted_sections",
        "detectable_format:multiple_sections",
        "detectable_content:postscript",
        "change_case:english_lowercase",
    },
    "combination:repeat_prompt": {
        "startend:quotation",
        "length_constraints:number_words",
        "detectable_format:constrained_response",
        "change_case:english_capital",
        "detectable_format:number_bullet_lists",
        "detectable_content:number_placeholders",
        "startend:end_checker",
        "keywords:letter_frequency",
        "keywords:forbidden_words",
        "keywords:frequency",
        "length_constraints:number_paragraphs",
        "length_constraints:nth_paragraph_first_word",
        "length_constraints:number_sentences",
        "language:response_language",
        "combination:repeat_prompt",
        "change_case:capital_word_frequency",
        "combination:two_responses",
        "detectable_format:json_format",
        "detectable_format:number_highlighted_sections",
        "detectable_format:multiple_sections",
        "detectable_content:postscript",
        "change_case:english_lowercase",
    },
    "startend:end_checker": {"startend:end_checker"},
    "change_case:capital_word_frequency": {
        "change_case:english_capital",
        "change_case:capital_word_frequency",
        "change_case:english_lowercase",
    },
    "change_case:english_capital": {"change_case:english_capital"},
    "change_case:english_lowercase": {
        "change_case:english_capital",
        "change_case:english_lowercase",
    },
    "punctuation:no_comma": {"punctuation:no_comma"},
    "startend:quotation": {"startend:quotation", "detectable_format:title"},
    # --- IFTrain out-of-distribution constraints ---
    "keywords:word_once": {"keywords:word_once"},
    "keywords:word_count_diff_numb": {"keywords:word_count_diff_numb"},
    "keywords:exclude_word_harder": {"keywords:exclude_word_harder"},
    "keywords:letter_counting2": {"keywords:letter_counting2", "keywords:letter_frequency"},
    "length_constraints:paragraphs_two_line_breaks": {
        "length_constraints:paragraphs_two_line_breaks",
        "length_constraints:number_paragraphs",
        "length_constraints:nth_paragraph_first_word",
        "length_constraints:counting_composition",
    },
    "startend:first_word_sent": {
        "startend:first_word_sent",
        "startend:first_word_answer",
    },
    "startend:first_word_answer": {
        "startend:first_word_answer",
        "startend:first_word_sent",
    },
    "startend:last_word_sent": {
        "startend:last_word_sent",
        "startend:last_word_answer",
        "startend:start_end_same_word",
    },
    "startend:last_word_answer": {
        "startend:last_word_answer",
        "startend:last_word_sent",
        "startend:start_end_same_word",
    },
    "detectable_format:bigram_wrapping": {"detectable_format:bigram_wrapping"},
    "combination:copying_simple": {
        "combination:copying_simple",
        "combination:copying_multiple",
        "combination:copy_instruction",
        "combination:copy_span_idx",
        "combination:repeat_prompt",
        "combination:two_responses",
        "combination:repeat_phrase",
    },
    "combination:copying_multiple": {
        "combination:copying_multiple",
        "combination:copying_simple",
        "combination:copy_instruction",
        "combination:copy_span_idx",
        "combination:repeat_prompt",
        "combination:two_responses",
        "combination:repeat_phrase",
    },
    "punctuation:no_dot": {
        "punctuation:no_dot",
        "length_constraints:number_sentences",
        "length_constraints:counting_composition",
    },
    "punctuation:no_exclamation": {"punctuation:no_exclamation"},
    "keywords:lowercase_counting": {"keywords:lowercase_counting"},
    "length_constraints:letter_total_count": {"length_constraints:letter_total_count"},
    "length_constraints:counting_composition": {
        "length_constraints:counting_composition",
        "length_constraints:number_paragraphs",
        "length_constraints:paragraphs_two_line_breaks",
        "length_constraints:number_sentences",
        "punctuation:no_dot",
    },
    "keywords:count_unique": {"keywords:count_unique"},
    "keywords:count_increment_word": {"keywords:count_increment_word"},
    "keywords:palindrome": {"keywords:palindrome"},
    "keywords:keyword_specific_pos": {"keywords:keyword_specific_pos"},
    "startend:start_end_same_word": {
        "startend:start_end_same_word",
        "startend:last_word_sent",
        "startend:last_word_answer",
    },
    "combination:repeat_phrase": {
        "combination:repeat_phrase",
        "combination:copying_simple",
        "combination:copying_multiple",
        "combination:copy_instruction",
        "combination:copy_span_idx",
    },
    "keywords:no_adjacent_consecutive": {"keywords:no_adjacent_consecutive"},
    "detectable_format:square_brackets_word": {
        "detectable_format:square_brackets_word",
        "detectable_content:number_placeholders",
    },
    "detectable_format:sentence_hyphens": {"detectable_format:sentence_hyphens"},
    "combination:copy_instruction": {
        "combination:copy_instruction",
        "combination:copying_simple",
        "combination:copying_multiple",
        "combination:copy_span_idx",
        "combination:repeat_prompt",
        "combination:two_responses",
        "combination:repeat_phrase",
    },
    "combination:copy_span_idx": {
        "combination:copy_span_idx",
        "combination:copying_simple",
        "combination:copying_multiple",
        "combination:copy_instruction",
        "combination:repeat_prompt",
        "combination:two_responses",
        "combination:repeat_phrase",
    },
}

LANGUAGE_TO_CODE = {
    "English": "en",
    "Spanish": "es",
    "Portuguese": "pt",
    "Arabic": "ar",
    "Hindi": "hi",
    "French": "fr",
    "Russian": "ru",
    "German": "de",
    "Japanese": "ja",
    "Italian": "it",
    "Bengali": "bn",
    "Ukrainian": "uk",
    "Thai": "th",
    "Urdu": "ur",
    "Tamil": "ta",
    "Telugu": "te",
    "Bulgarian": "bg",
    "Korean": "ko",
    "Polish": "pl",
    "Hebrew": "he",
    "Persian": "fa",
    "Vietnamese": "vi",
    "Nepali": "ne",
    "Swahili": "sw",
    "Kannada": "kn",
    "Marathi": "mr",
    "Gujarati": "gu",
    "Punjabi": "pa",
    "Malayalam": "ml",
    "Finnish": "fi",
}

RELATION_PT_TO_EN = {
    "menos de": "less than",
    "pelo menos": "at least",
}

def build_instruction_kwargs(row: dict) -> dict:
    """Builds the list of `kwargs` for each instruction in `instruction_id_list`."""
    kwargs = row["kwargs"]

    if kwargs is None:
        return {"valid_kwargs_json": False}

    try:
        kwargs = json.loads(row["kwargs"])
    except json.JSONDecodeError:
        return {"valid_kwargs_json": False}

    instruction_id_list = row["instruction_id_list"]
    kwargs_list = []
    for instruction_id in instruction_id_list:
        args = INSTRUCTION_ARGS[instruction_id]
        instruction_kwargs = {}
        for arg in args:
            value = kwargs[arg]
            if arg == "language":
                if value in LANGUAGE_TO_CODE:
                    value = LANGUAGE_TO_CODE[value]
                elif value not in LANGUAGE_TO_CODE.values():
                    return {"valid_kwargs_json": False}
            # Normalize Portuguese relation values to English for lm-eval
            elif arg in ("relation", "let_relation", "capital_relation"):
                if value in RELATION_PT_TO_EN:
                    value = RELATION_PT_TO_EN[value]
            instruction_kwargs[arg] = value
        kwargs_list.append(instruction_kwargs)

    return {"kwargs": json.dumps(kwargs_list), "valid_kwargs_json": True}


def filter_not_valid_rows(row: dict) -> bool:
    """Filters out rows which their JSON kwargs are not valid or that the instructions
    in their `instruction_id_list` conflict each other."""
    valid_kwargs_json = row["valid_kwargs_json"]
    if not valid_kwargs_json:
        return False

    instruction_id_list = row["instruction_id_list"]
    for instruction_id in instruction_id_list:
        conflicts = IFEVAL_INSTRUCTION_CONFLICTS[instruction_id]
        if any(
            conflict in instruction_id_list
            for conflict in conflicts
            if conflict != instruction_id
        ):
            return False

    return True


def get_ifeval_results(row: dict) -> dict:
    """Checks if the `response` correct is OK using the IFEval benchmark code from `lm-evaluation-harness`."""
    results = [row["response"]]
    doc = row.copy()
    doc["kwargs"] = json.loads(doc["kwargs"])
    try:
        return process_results(doc, results)
    except Exception as e:
        return {
            "prompt_level_strict_acc": False,
            "inst_level_strict_acc": [],
            "prompt_level_loose_acc": False,
            "inst_level_loose_acc": [],
            "validation_error": str(e),  # Capture the actual error
        }


def get_dataset() -> "Dataset":
    dataset = load_dataset("argilla/ifeval-like-data", split="train")
    dataset = dataset.map(build_instruction_kwargs)
    dataset = dataset.filter(filter_not_valid_rows)
    dataset = dataset.add_column("key", list(range(len(dataset))))
    dataset = dataset.rename_column("instruction", "prompt")
    dataset = dataset.select_columns(
        ["key", "prompt", "response", "instruction_id_list", "kwargs"]
    )
    dataset = dataset.map(get_ifeval_results)
    dataset = dataset.filter(lambda x: x["prompt_level_strict_acc"])
    return dataset


if __name__ == "__main__":
    dataset = get_dataset()
    dataset.push_to_hub("argilla/ifeval-like-data", config_name="filtered")
