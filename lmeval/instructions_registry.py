# Copyright 2023 The Google Research Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Registry of all instructions."""

from lmeval import instructions


_KEYWORD = "keywords:"

_LANGUAGE = "language:"

_LENGTH = "length_constraints:"

_CONTENT = "detectable_content:"

_FORMAT = "detectable_format:"

_MULTITURN = "multi-turn:"

_COMBINATION = "combination:"

_STARTEND = "startend:"

_CHANGE_CASES = "change_case:"

_PUNCTUATION = "punctuation:"

INSTRUCTION_DICT = {
    _KEYWORD + "existence": instructions.KeywordChecker,
    _KEYWORD + "frequency": instructions.KeywordFrequencyChecker,
    # TODO(jeffreyzhou): make a proper set of sentences to choose from
    # _KEYWORD + "key_sentences": instructions.KeySentenceChecker,
    _KEYWORD + "forbidden_words": instructions.ForbiddenWords,
    _KEYWORD + "letter_frequency": instructions.LetterFrequencyChecker,
    _LANGUAGE + "response_language": instructions.ResponseLanguageChecker,
    _LENGTH + "number_sentences": instructions.NumberOfSentences,
    _LENGTH + "number_paragraphs": instructions.ParagraphChecker,
    _LENGTH + "number_words": instructions.NumberOfWords,
    _LENGTH + "nth_paragraph_first_word": instructions.ParagraphFirstWordCheck,
    _CONTENT + "number_placeholders": instructions.PlaceholderChecker,
    _CONTENT + "postscript": instructions.PostscriptChecker,
    _FORMAT + "number_bullet_lists": instructions.BulletListChecker,
    # TODO(jeffreyzhou): Pre-create paragraph or use prompt to replace
    # _CONTENT + "rephrase_paragraph": instructions.RephraseParagraph,
    _FORMAT + "constrained_response": instructions.ConstrainedResponseChecker,
    _FORMAT + "number_highlighted_sections": (instructions.HighlightSectionChecker),
    _FORMAT + "multiple_sections": instructions.SectionChecker,
    # TODO(tianjianlu): Re-enable rephrasing with preprocessing the message.
    # _FORMAT + "rephrase": instructions.RephraseChecker,
    _FORMAT + "json_format": instructions.JsonFormat,
    _FORMAT + "title": instructions.TitleChecker,
    # TODO(tianjianlu): Re-enable with specific prompts.
    # _MULTITURN + "constrained_start": instructions.ConstrainedStartChecker,
    _COMBINATION + "two_responses": instructions.TwoResponsesChecker,
    _COMBINATION + "repeat_prompt": instructions.RepeatPromptThenAnswer,
    _STARTEND + "end_checker": instructions.EndChecker,
    _CHANGE_CASES + "capital_word_frequency": instructions.CapitalWordFrequencyChecker,
    _CHANGE_CASES + "english_capital": instructions.CapitalLettersEnglishChecker,
    _CHANGE_CASES + "english_lowercase": instructions.LowercaseLettersEnglishChecker,
    _PUNCTUATION + "no_comma": instructions.CommaChecker,
    _STARTEND + "quotation": instructions.QuotationChecker,
    # --- IFTrain out-of-distribution constraints ---
    _KEYWORD + "word_once": instructions.KeywordOnceChecker,
    _KEYWORD + "word_count_diff_numb": instructions.KeywordExactCountChecker,
    _KEYWORD + "exclude_word_harder": instructions.ExcludeWordHarderChecker,
    _KEYWORD + "letter_counting2": instructions.LetterExactCountChecker,
    _LENGTH + "paragraphs_two_line_breaks": instructions.ParagraphsTwoLineBreaksChecker,
    _STARTEND + "first_word_sent": instructions.FirstWordSentenceChecker,
    _STARTEND + "first_word_answer": instructions.FirstWordAnswerChecker,
    _STARTEND + "last_word_sent": instructions.LastWordSentenceChecker,
    _STARTEND + "last_word_answer": instructions.LastWordAnswerChecker,
    _FORMAT + "bigram_wrapping": instructions.BigramWrappingChecker,
    _COMBINATION + "copying_simple": instructions.CopyingSimpleChecker,
    _COMBINATION + "copying_multiple": instructions.CopyingMultipleChecker,
    _PUNCTUATION + "no_dot": instructions.NoDotChecker,
    _PUNCTUATION + "no_exclamation": instructions.NoExclamationChecker,
    _KEYWORD + "lowercase_counting": instructions.LowercaseWordCountChecker,
    _LENGTH + "letter_total_count": instructions.LetterTotalCountChecker,
    _LENGTH + "counting_composition": instructions.CountingCompositionChecker,
    _KEYWORD + "count_unique": instructions.UniqueWordsChecker,
    _KEYWORD + "count_increment_word": instructions.IncrementKeywordChecker,
    _KEYWORD + "palindrome": instructions.PalindromeChecker,
    _KEYWORD + "keyword_specific_pos": instructions.KeywordSpecificPositionChecker,
    _STARTEND + "start_end_same_word": instructions.StartEndSameWordChecker,
    _COMBINATION + "repeat_phrase": instructions.RepeatPhraseChecker,
    _KEYWORD + "no_adjacent_consecutive": instructions.NoAdjacentConsecutiveLettersChecker,
    _FORMAT + "square_brackets_word": instructions.SquareBracketsWordChecker,
    _FORMAT + "sentence_hyphens": instructions.SentenceHyphensChecker,
    _COMBINATION + "copy_instruction": instructions.CopyInstructionChecker,
    _COMBINATION + "copy_span_idx": instructions.CopySpanIndexChecker,
}

INSTRUCTION_CONFLICTS = {
    _KEYWORD + "existence": {_KEYWORD + "existence"},
    _KEYWORD + "frequency": {_KEYWORD + "frequency"},
    # TODO(jeffreyzhou): make a proper set of sentences to choose from
    # _KEYWORD + "key_sentences": instructions.KeySentenceChecker,
    _KEYWORD + "forbidden_words": {_KEYWORD + "forbidden_words"},
    _KEYWORD + "letter_frequency": {_KEYWORD + "letter_frequency"},
    _LANGUAGE + "response_language": {
        _LANGUAGE + "response_language",
        _FORMAT + "multiple_sections",
        _KEYWORD + "existence",
        _KEYWORD + "frequency",
        _KEYWORD + "forbidden_words",
        _STARTEND + "end_checker",
        _CHANGE_CASES + "english_capital",
        _CHANGE_CASES + "english_lowercase",
    },
    _LENGTH + "number_sentences": {_LENGTH + "number_sentences"},
    _LENGTH + "number_paragraphs": {
        _LENGTH + "number_paragraphs",
        _LENGTH + "nth_paragraph_first_word",
        _LENGTH + "number_sentences",
        _LENGTH + "nth_paragraph_first_word",
        _LENGTH + "paragraphs_two_line_breaks",
        _LENGTH + "counting_composition",
    },
    _LENGTH + "number_words": {_LENGTH + "number_words"},
    _LENGTH + "nth_paragraph_first_word": {
        _LENGTH + "nth_paragraph_first_word",
        _LENGTH + "number_paragraphs",
        _LENGTH + "paragraphs_two_line_breaks",
    },
    _CONTENT + "number_placeholders": {_CONTENT + "number_placeholders"},
    _CONTENT + "postscript": {_CONTENT + "postscript"},
    _FORMAT + "number_bullet_lists": {_FORMAT + "number_bullet_lists"},
    # TODO(jeffreyzhou): Pre-create paragraph or use prompt to replace
    # _CONTENT + "rephrase_paragraph": instructions.RephraseParagraph,
    _FORMAT + "constrained_response": set(INSTRUCTION_DICT.keys()),
    _FORMAT + "number_highlighted_sections": {_FORMAT + "number_highlighted_sections"},
    _FORMAT + "multiple_sections": {
        _FORMAT + "multiple_sections",
        _LANGUAGE + "response_language",
        _FORMAT + "number_highlighted_sections",
    },
    # TODO(tianjianlu): Re-enable rephrasing with preprocessing the message.
    # _FORMAT + "rephrase": instructions.RephraseChecker,
    _FORMAT + "json_format": set(INSTRUCTION_DICT.keys()).difference(
        {_KEYWORD + "forbidden_words", _KEYWORD + "existence"}
    ),
    _FORMAT + "title": {_FORMAT + "title"},
    # TODO(tianjianlu): Re-enable with specific prompts.
    # _MULTITURN + "constrained_start": instructions.ConstrainedStartChecker,
    _COMBINATION + "two_responses": set(INSTRUCTION_DICT.keys()).difference(
        {
            _KEYWORD + "forbidden_words",
            _KEYWORD + "existence",
            _LANGUAGE + "response_language",
            _FORMAT + "title",
            _PUNCTUATION + "no_comma",
        }
    ),
    _COMBINATION + "repeat_prompt": set(INSTRUCTION_DICT.keys()).difference(
        {_KEYWORD + "existence", _FORMAT + "title", _PUNCTUATION + "no_comma"}
    ),
    _STARTEND + "end_checker": {_STARTEND + "end_checker"},
    _CHANGE_CASES + "capital_word_frequency": {
        _CHANGE_CASES + "capital_word_frequency",
        _CHANGE_CASES + "english_lowercase",
        _CHANGE_CASES + "english_capital",
    },
    _CHANGE_CASES + "english_capital": {_CHANGE_CASES + "english_capital"},
    _CHANGE_CASES + "english_lowercase": {
        _CHANGE_CASES + "english_lowercase",
        _CHANGE_CASES + "english_capital",
    },
    _PUNCTUATION + "no_comma": {_PUNCTUATION + "no_comma"},
    _STARTEND + "quotation": {_STARTEND + "quotation", _FORMAT + "title"},
    # --- IFTrain out-of-distribution constraints ---
    _KEYWORD + "word_once": {_KEYWORD + "word_once"},
    _KEYWORD + "word_count_diff_numb": {_KEYWORD + "word_count_diff_numb"},
    _KEYWORD + "exclude_word_harder": {_KEYWORD + "exclude_word_harder"},
    _KEYWORD + "letter_counting2": {_KEYWORD + "letter_counting2", _KEYWORD + "letter_frequency"},
    _LENGTH + "paragraphs_two_line_breaks": {
        _LENGTH + "paragraphs_two_line_breaks",
        _LENGTH + "number_paragraphs",
        _LENGTH + "nth_paragraph_first_word",
        _LENGTH + "counting_composition",
    },
    _STARTEND + "first_word_sent": {
        _STARTEND + "first_word_sent",
        _STARTEND + "first_word_answer",
    },
    _STARTEND + "first_word_answer": {
        _STARTEND + "first_word_answer",
        _STARTEND + "first_word_sent",
    },
    _STARTEND + "last_word_sent": {
        _STARTEND + "last_word_sent",
        _STARTEND + "last_word_answer",
        _STARTEND + "start_end_same_word",
    },
    _STARTEND + "last_word_answer": {
        _STARTEND + "last_word_answer",
        _STARTEND + "last_word_sent",
        _STARTEND + "start_end_same_word",
    },
    _FORMAT + "bigram_wrapping": {_FORMAT + "bigram_wrapping"},
    _COMBINATION + "copying_simple": set(INSTRUCTION_DICT.keys()).difference(
        {_COMBINATION + "copying_simple"}
    ),
    _COMBINATION + "copying_multiple": set(INSTRUCTION_DICT.keys()).difference(
        {_COMBINATION + "copying_multiple"}
    ),
    _PUNCTUATION + "no_dot": {
        _PUNCTUATION + "no_dot",
        _LENGTH + "number_sentences",
        _LENGTH + "counting_composition",
    },
    _PUNCTUATION + "no_exclamation": {_PUNCTUATION + "no_exclamation"},
    _KEYWORD + "lowercase_counting": {_KEYWORD + "lowercase_counting"},
    _LENGTH + "letter_total_count": {_LENGTH + "letter_total_count"},
    _LENGTH + "counting_composition": {
        _LENGTH + "counting_composition",
        _LENGTH + "number_paragraphs",
        _LENGTH + "paragraphs_two_line_breaks",
        _LENGTH + "number_sentences",
        _PUNCTUATION + "no_dot",
    },
    _KEYWORD + "count_unique": {_KEYWORD + "count_unique"},
    _KEYWORD + "count_increment_word": {_KEYWORD + "count_increment_word"},
    _KEYWORD + "palindrome": {_KEYWORD + "palindrome"},
    _KEYWORD + "keyword_specific_pos": {_KEYWORD + "keyword_specific_pos"},
    _STARTEND + "start_end_same_word": {
        _STARTEND + "start_end_same_word",
        _STARTEND + "last_word_sent",
        _STARTEND + "last_word_answer",
    },
    _COMBINATION + "repeat_phrase": {_COMBINATION + "repeat_phrase"},
    _KEYWORD + "no_adjacent_consecutive": {_KEYWORD + "no_adjacent_consecutive"},
    _FORMAT + "square_brackets_word": {
        _FORMAT + "square_brackets_word",
        _CONTENT + "number_placeholders",
    },
    _FORMAT + "sentence_hyphens": {_FORMAT + "sentence_hyphens"},
    _COMBINATION + "copy_instruction": set(INSTRUCTION_DICT.keys()).difference(
        {_COMBINATION + "copy_instruction"}
    ),
    _COMBINATION + "copy_span_idx": set(INSTRUCTION_DICT.keys()).difference(
        {_COMBINATION + "copy_span_idx"}
    ),
}


def conflict_make(conflicts):
    """Makes sure if A conflicts with B, B will conflict with A.

    Args:
      conflicts: Dictionary of potential conflicts where key is instruction id
        and value is set of instruction ids that it conflicts with.

    Returns:
      Revised version of the dictionary. All instructions conflict with
      themselves. If A conflicts with B, B will conflict with A.
    """
    for key in conflicts:
        for k in conflicts[key]:
            conflicts[k].add(key)
        conflicts[key].add(key)
    return conflicts
