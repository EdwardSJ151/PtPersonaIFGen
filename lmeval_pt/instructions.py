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

"""Library of instructions."""

import collections
import json
import logging
import random
import re
import string
from typing import Dict, Optional, Sequence, Union

import langdetect

from lmeval_pt import instructions_util


logger = logging.getLogger(__name__)

_InstructionArgsDtype = Optional[Dict[str, Union[int, str, Sequence[str]]]]

_LANGUAGES = instructions_util.LANGUAGE_CODES

# The relational operation for comparison.
_COMPARISON_RELATION = ("less than", "at least")

# The maximum number of sentences.
_MAX_NUM_SENTENCES = 20

# The number of placeholders.
_NUM_PLACEHOLDERS = 4

# The number of bullet lists.
_NUM_BULLETS = 5

# The options of constrained response.
_CONSTRAINED_RESPONSE_OPTIONS = (
    "My answer is yes.",
    "My answer is no.",
    "My answer is maybe.",
)

# The options of starter keywords.
_STARTER_OPTIONS = (
    "I would say",
    "My answer is",
    "I believe",
    "In my opinion",
    "I think",
    "I reckon",
    "I feel",
    "From my perspective",
    "As I see it",
    "According to me",
    "As far as I'm concerned",
    "To my understanding",
    "In my view",
    "My take on it is",
    "As per my perception",
)

# The options of ending keywords.
# TODO(jeffreyzhou) add more ending options
_ENDING_OPTIONS = ("Any other questions?", "Is there anything else I can help with?")

# The number of highlighted sections.
_NUM_HIGHLIGHTED_SECTIONS = 4

# The section splitter.
_SECTION_SPLITER = ("Section", "SECTION")

# The number of sections.
_NUM_SECTIONS = 5

# The number of paragraphs.
_NUM_PARAGRAPHS = 5

# The postscript marker.
_POSTSCRIPT_MARKER = ("P.S.", "P.P.S")

# The number of keywords.
_NUM_KEYWORDS = 2

# The occurrences of a single keyword.
_KEYWORD_FREQUENCY = 3

# The occurrences of a single letter.
_LETTER_FREQUENCY = 10

# The occurrences of words with all capital letters.
_ALL_CAPITAL_WORD_FREQUENCY = 20

# The number of words in the response.
_NUM_WORDS_LOWER_LIMIT = 100
_NUM_WORDS_UPPER_LIMIT = 500


class Instruction:
    """An instruction template."""

    def __init__(self, instruction_id):
        self.id = instruction_id

    def build_description(self, **kwargs):
        raise NotImplementedError("`build_description` not implemented.")

    def get_instruction_args(self):
        raise NotImplementedError("`get_instruction_args` not implemented.")

    def get_instruction_args_keys(self):
        raise NotImplementedError("`get_instruction_args_keys` not implemented.")

    def check_following(self, value):
        raise NotImplementedError("`check_following` not implemented.")


class ResponseLanguageChecker(Instruction):
    """Check the language of the entire response."""

    def build_description(self, *, language=None):
        """Build the instruction description.

        Args:
          language: A string representing the expected language of the response. The
            language has to comply to the 97 types defined in
            `langid.py` (https://pypi.org/project/langid/1.1.5/), which follows
            ISO 639-1 codes (https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes);
            for example, `en` for English, `zh` for Chinese, `fr` for French.

        Returns:
          A string representing the instruction description.
        """
        self._language = language
        if self._language is None:
            self._language = random.choice(list(_LANGUAGES.keys()))
        # TODO(tianjianlu): opens the description generation to more choices.
        self._description_pattern = (
            "Your ENTIRE response should be in {language} language, no other "
            + "language is allowed."
        )
        return self._description_pattern.format(language=_LANGUAGES[self._language])

    def get_instruction_args(self):
        """Returns the keyword args of `build_description`."""
        return {"language": self._language}

    def get_instruction_args_keys(self):
        """Returns the args keys of `build_description`."""
        return ["language"]

    def check_following(self, value):
        """Check if the language of the entire response follows the instruction.

        Args:
          value: A string representing the response.

        Returns:
          True if the language of `value` follows instruction; otherwise False.
        """
        assert isinstance(value, str)

        try:
            return langdetect.detect(value) == self._language
        except langdetect.LangDetectException as e:
            # Count as instruction is followed.
            logging.error(
                "Unable to detect language for text %s due to %s", value, e
            )  # refex: disable=pytotw.037
            return True


class NumberOfSentences(Instruction):
    """Check the number of sentences."""

    def build_description(self, *, num_sentences=None, relation=None):
        """Build the instruction description.

        Args:
          num_sentences: An integer specifying the number of sentences as a
            threshold.
          relation: A string in (`less than`, `at least`), defining the relational
            operator for comparison.
            Two relational comparisons are supported for now:
            if 'less than', the actual number of sentences < the threshold;
            if 'at least', the actual number of sentences >= the threshold.

        Returns:
          A string representing the instruction description.
        """
        # The number of sentences as a threshold for comparison.
        self._num_sentences_threshold = num_sentences
        if self._num_sentences_threshold is None or self._num_sentences_threshold < 0:
            self._num_sentences_threshold = random.randint(1, _MAX_NUM_SENTENCES)

        if relation is None:
            self._comparison_relation = random.choice(_COMPARISON_RELATION)
        elif relation not in _COMPARISON_RELATION:
            raise ValueError(
                "The supported relation for comparison must be in "
                f"{_COMPARISON_RELATION}, but {relation} is given."
            )
        else:
            self._comparison_relation = relation

        self._description_pattern = (
            "Your response should contain {relation} {num_sentences} sentences."
        )
        return self._description_pattern.format(
            relation=self._comparison_relation,
            num_sentences=self._num_sentences_threshold,
        )

    def get_instruction_args(self):
        """Returns the keyword args of `build_description`."""
        return {
            "num_sentences": self._num_sentences_threshold,
            "relation": self._comparison_relation,
        }

    def get_instruction_args_keys(self):
        """Returns the args keys of `build_description`."""
        return ["num_sentences", "relation"]

    def check_following(self, value):
        """Check if the number of sentences follows the instruction.

        Args:
          value: A string representing the response.

        Returns:
          True if the response follows the instruction.

        Raise:
            ValueError if the string in `instruction_args` is not in
            [`less_than`, `at_least`].
        """
        num_sentences = instructions_util.count_sentences(value)
        if self._comparison_relation == _COMPARISON_RELATION[0]:
            return num_sentences < self._num_sentences_threshold
        elif self._comparison_relation == _COMPARISON_RELATION[1]:
            return num_sentences >= self._num_sentences_threshold


class PlaceholderChecker(Instruction):
    """Check the placeholders in template writing."""

    def build_description(self, *, num_placeholders=None):
        """Build the instruction description.

        Args:
          num_placeholders: An integer denoting the minimum number of
            placeholders required in the response.

        Returns:
          A string representing the instruction description.
        """
        self._num_placeholders = num_placeholders
        if self._num_placeholders is None or self._num_placeholders < 0:
            self._num_placeholders = random.randint(1, _NUM_PLACEHOLDERS)
        self._description_pattern = (
            "The response must contain at least {num_placeholders} placeholders "
            + "represented by square brackets, such as [address]."
        )
        return self._description_pattern.format(num_placeholders=self._num_placeholders)

    def get_instruction_args(self):
        """Returns the keyword args of `build_description`."""
        return {"num_placeholders": self._num_placeholders}

    def get_instruction_args_keys(self):
        """Returns the args keys of `build_description`."""
        return ["num_placeholders"]

    def check_following(self, value):
        """Check if the number of placeholders follows the instruction.

        Args:
          value: A string representing the response.

        Returns:
          True if the actual number of placeholders in the response is greater than
          or equal to `num_placeholders`; otherwise, False.
        """
        placeholders = re.findall(r"\[.*?\]", value)
        num_placeholders = len(placeholders)
        return num_placeholders >= self._num_placeholders


class BulletListChecker(Instruction):
    """Checks the bullet list in the prompt."""

    def build_description(self, *, num_bullets=None):
        """Build the instruction description.

        Args:
          num_bullets: An integer specifying the exact number of bullet lists
            that is required to appear in the response.

        Returns:
          A string representing the instruction description.
        """
        self._num_bullets = num_bullets
        if self._num_bullets is None or self._num_bullets < 0:
            self._num_bullets = random.randint(1, _NUM_BULLETS)
        self._description_pattern = (
            "Your answer must contain exactly {num_bullets} bullet points. "
            + "Use the markdown bullet points such as:\n"
            + "* This is point 1. \n"
            + "* This is point 2"
        )
        return self._description_pattern.format(num_bullets=self._num_bullets)

    def get_instruction_args(self):
        """Returns the keyword args of `build_description`."""
        return {"num_bullets": self._num_bullets}

    def get_instruction_args_keys(self):
        """Returns the args keys of `build_description`."""
        return ["num_bullets"]

    def check_following(self, value):
        r"""Check if the number of bullet lists meets the requirement.

        Args:
          value: A string representing the response. The response is expected to
            contain some bullet lists that start with `\*`.

        Returns:
          True if the actual number of bullet lists in the response meets the
          requirement.
        """
        bullet_lists = re.findall(r"^\s*\*[^\*].*$", value, flags=re.MULTILINE)
        bullet_lists_2 = re.findall(r"^\s*-.*$", value, flags=re.MULTILINE)
        num_bullet_lists = len(bullet_lists) + len(bullet_lists_2)
        return num_bullet_lists == self._num_bullets


class ConstrainedResponseChecker(Instruction):
    """Checks the constrained response."""

    def build_description(self):
        """Build the instruction description."""
        # A sequence of string(s) representing the options of the expected response.
        self._constrained_responses = _CONSTRAINED_RESPONSE_OPTIONS
        self._description_pattern = (
            "Answer with one of the following options: {response_options}"
        )
        return self._description_pattern.format(
            response_options=self._constrained_responses
        )

    def get_instruction_args(self):
        """Returns the keyword args of `build_description`."""
        return None

    def get_instruction_args_keys(self):
        """Returns the args keys of `build_description`."""
        return []

    def check_following(self, value):
        """Checks if the response matches the constrained options.

        Args:
          value: A string representing the response.

        Returns:
          True if the actual response contains one of the options in the constrained
          responses; otherwise False.
        """
        value = value.strip()
        for constrained_response in self._constrained_responses:
            if constrained_response in value:
                return True
        return False


class ConstrainedStartChecker(Instruction):
    """Checks the response start."""

    def build_description(self, *, starter=None):
        """Build the instruction description.

        Args:
          starter: A string representing the keyword that the response should start
            with.

        Returns:
          A string representing the instruction description.
        """
        self._starter = starter.strip() if isinstance(starter, str) else starter
        if self._starter is None:
            self._starter = random.choice(_STARTER_OPTIONS)
        self._description_pattern = (
            "During the conversation, when it is your turn, "
            + "please always start with {starter}"
        )
        return self._description_pattern.format(starter=self._starter)

    def get_instruction_args(self):
        """Returns the keyword args of `build_description`."""
        return {"starter": self._starter}

    def get_instruction_args_keys(self):
        """Returns the args keys of `build_description`."""
        return ["starter"]

    def check_following(self, value):
        """Checks if the response starts with the constrained keyword or phrase.

        Args:
          value: A string representing the response.

        Returns:
          True if the response starts with the given phrase or keyword that is
          contained in `instruction_args`; otherwise, False.
        """
        response_pattern = r"^\s*" + self._starter + r".*$"
        response_with_constrained_start = re.search(
            response_pattern, value, flags=re.MULTILINE
        )
        return True if response_with_constrained_start else False


class HighlightSectionChecker(Instruction):
    """Checks the highlighted section."""

    def build_description(self, *, num_highlights=None):
        """Build the instruction description.

        Args:
          num_highlights: An integer specifying the minimum number of highlighted
            sections.

        Returns:
          A string representing the instruction description.
        """
        self._num_highlights = num_highlights
        if self._num_highlights is None or self._num_highlights < 0:
            self._num_highlights = random.randint(1, _NUM_HIGHLIGHTED_SECTIONS)

        self._description_pattern = (
            "Highlight at least {num_highlights} sections in your answer with "
            + "markdown, i.e. *highlighted section*."
        )

        return self._description_pattern.format(num_highlights=self._num_highlights)

    def get_instruction_args(self):
        """Returns the keyword args of `build_description`."""
        return {"num_highlights": self._num_highlights}

    def get_instruction_args_keys(self):
        """Returns the args keys of `build_description`."""
        return ["num_highlights"]

    def check_following(self, value):
        """Checks if the number of highlighted sections meets the requirement.

        Args:
          value: a string representing the response. The response is expected to
            contain highlighted sections in the format of *highlighted*.

        Returns:
          True if the actual number of highlighted sections in the format of
          *highlighted sections* meets the minimum requirement; otherwise False.
        """
        num_highlights = 0
        highlights = re.findall(r"\*[^\n\*]*\*", value)
        double_highlights = re.findall(r"\*\*[^\n\*]*\*\*", value)
        for highlight in highlights:
            if highlight.strip("*").strip():
                num_highlights += 1
        for highlight in double_highlights:
            if highlight.removeprefix("**").removesuffix("**").strip():
                num_highlights += 1

        return num_highlights >= self._num_highlights


class SectionChecker(Instruction):
    """Checks the sections."""

    def build_description(self, *, section_spliter=None, num_sections=None):
        """Build the instruction description.

        Args:
          section_spliter: A string represents the section spliter keyword that
            marks a new section, i.e., `Section` or `SECTION`.
          num_sections: An integer specifying the number of sections.

        Returns:
          A string representing the instruction description.
        """
        self._section_spliter = (
            section_spliter.strip()
            if isinstance(section_spliter, str)
            else section_spliter
        )
        if self._section_spliter is None:
            self._section_spliter = random.choice(_SECTION_SPLITER)

        self._num_sections = num_sections
        if self._num_sections is None or self._num_sections < 0:
            self._num_sections = random.randint(1, _NUM_SECTIONS)

        self._description_pattern = (
            "Your response must have {num_sections} sections. Mark the beginning "
            + "of each section with {section_spliter} X, such as:\n"
            + "{section_spliter} 1\n"
            + "[content of section 1]\n"
            + "{section_spliter} 2\n"
            + "[content of section 2]"
        )

        return self._description_pattern.format(
            num_sections=self._num_sections, section_spliter=self._section_spliter
        )

    def get_instruction_args(self):
        """Returns the keyword args of `build_description`."""
        return {
            "section_spliter": self._section_spliter,
            "num_sections": self._num_sections,
        }

    def get_instruction_args_keys(self):
        """Returns the args keys of `build_description`."""
        return ["section_spliter", "num_sections"]

    def check_following(self, value):
        """Checks the response contains multiple sections.

        Args:
          value: A string representing the response. The response is expected
            to contain multiple sections (number of sections is greater than 1).
            A new section starts with `Section 1`, where the number denotes the
            section index.

        Returns:
          True if the number of sections in the response is greater than or equal to
          the minimum number of sections; otherwise, False.
        """
        section_splitter_patten = r"\s?" + self._section_spliter + r"\s?\d+\s?"
        sections = re.split(section_splitter_patten, value)
        num_sections = len(sections) - 1
        return num_sections >= self._num_sections


class ParagraphChecker(Instruction):
    """Checks the paragraphs."""

    def build_description(self, *, num_paragraphs=None):
        """Build the instruction description.

        Args:
          num_paragraphs: An integer specifying the number of paragraphs.

        Returns:
          A string representing the instruction description.
        """
        self._num_paragraphs = num_paragraphs
        if self._num_paragraphs is None or self._num_paragraphs < 0:
            self._num_paragraphs = random.randint(1, _NUM_PARAGRAPHS)

        self._description_pattern = (
            "There should be {num_paragraphs} paragraphs. "
            + "Paragraphs are separated with the markdown divider: ***"
        )

        return self._description_pattern.format(num_paragraphs=self._num_paragraphs)

    def get_instruction_args(self):
        """Returns the keyword args of `build_description`."""
        return {"num_paragraphs": self._num_paragraphs}

    def get_instruction_args_keys(self):
        """Returns the args keys of `build_description`."""
        return ["num_paragraphs"]

    def check_following(self, value):
        """Checks the response contains required number of paragraphs.

        Args:
          value: A string representing the response. The response may contain
            paragraphs that are separated by the markdown divider: `***`.

        Returns:
          True if the actual number of paragraphs is the same as required;
          otherwise, False.
        """
        paragraphs = re.split(r"\s?\*\*\*\s?", value)
        num_paragraphs = len(paragraphs)

        for index, paragraph in enumerate(paragraphs):
            if not paragraph.strip():
                if index == 0 or index == len(paragraphs) - 1:
                    num_paragraphs -= 1
                else:
                    return False

        return num_paragraphs == self._num_paragraphs


class PostscriptChecker(Instruction):
    """Checks the postscript."""

    def build_description(self, *, postscript_marker=None):
        """Build the instruction description.

        Args:
          postscript_marker: A string containing the keyword that marks the start
            of the postscript section.

        Returns:
          A string representing the instruction description.
        """
        self._postscript_marker = (
            postscript_marker.strip()
            if isinstance(postscript_marker, str)
            else postscript_marker
        )
        if self._postscript_marker is None:
            self._postscript_marker = random.choice(_POSTSCRIPT_MARKER)

        self._description_pattern = (
            "At the end of your response, please explicitly add a postscript "
            + "starting with {postscript}"
        )

        return self._description_pattern.format(postscript=self._postscript_marker)

    def get_instruction_args(self):
        """Returns the keyword args of `build_description`."""
        return {"postscript_marker": self._postscript_marker}

    def get_instruction_args_keys(self):
        """Returns the args keys of `build_description`."""
        return ["postscript_marker"]

    def check_following(self, value):
        """Checks if the response follows the postscript format.

        Args:
          value: a string representing the response. The response is expected to
            contain a postscript section.

        Returns:
          True if the response contains a postscript section starting with
          the keyword containing in the `instruction_args`; otherwise False.
        """
        value = value.lower()
        if self._postscript_marker == "P.P.S":
            postscript_pattern = r"\s*p\.\s?p\.\s?s.*$"
        elif self._postscript_marker == "P.S.":
            postscript_pattern = r"\s*p\.\s?s\..*$"
        else:
            postscript_pattern = r"\s*" + self._postscript_marker.lower() + r".*$"
        postscript = re.findall(postscript_pattern, value, flags=re.MULTILINE)
        return True if postscript else False


class RephraseChecker(Instruction):
    """Checks the rephrase."""

    def build_description(self, *, original_message):
        """Build the instruction description.

        Args:
          original_message: A string representing the original message. The
            rephrased response should only change its words/sentences in between
            its two asterisks, for example, *change me*. Both original and rephrased
            messages should contain the changes in the form of *change me*.

        Returns:
          A string representing the instruction description.
        """
        if not self.is_change(original_message):
            raise ValueError(
                f"Message {original_message} does not contain changes "
                "in the form of *change me*."
            )

        self._reference_without_change = original_message
        self._description = (
            "Rephrasing: Your rephrased response should only"
            + "change the words/sentences in between two asterisks"
            + "such as *change me*."
        )
        return self._description

    def get_instruction_args(self):
        """Returns the keyword args of `build_description`."""
        return {"original_message": self._reference_without_change}

    def get_instruction_args_keys(self):
        """Returns the args keys of `build_description`."""
        return ["original_message"]

    def check_following(self, value):
        r"""Checks if the rephrasing follows the instruction.

        Args:
          value: A string representing the response, which is expected to rephras
            the string of `instruction_args`.

        Returns:
          True if `value` and `instruction_args` only differ by the words/sentences
          in between two asterisks such as *change me*; otherwise, False.
        """

        if not self.is_change(value):
            raise ValueError(
                f"value {value} does not contain changes in the form of *change me*."
            )

        response_without_changes = self.strip_changes(value)
        reference_without_changes = self.strip_changes(self._reference_without_change)

        return response_without_changes == reference_without_changes

    def is_change(self, response):
        """Check if there is change in the response in the form of *change me*."""
        return re.search(r"\*.*\*", response)

    def strip_changes(self, response):
        """Strips off the changes."""
        return re.sub(r"\*.*\*", "", response)


class KeywordChecker(Instruction):
    """Check the existence of certain keywords."""

    def build_description(self, *, keywords=None):
        """Build the instruction description.

        Args:
          keywords: A sequence of strings representing the keywords that are
            expected in the response.

        Returns:
          A string representing the instruction description.
        """

        if not keywords:
            self._keywords = instructions_util.generate_keywords(
                num_keywords=_NUM_KEYWORDS
            )
        else:
            self._keywords = keywords
        self._keywords = sorted(self._keywords)

        self._description_pattern = "Include keywords {keywords} in the response."

        return self._description_pattern.format(keywords=self._keywords)

    def get_instruction_args(self):
        """Returns the keyword args of `build_description`."""
        return {"keywords": self._keywords}

    def get_instruction_args_keys(self):
        """Returns the args keys of `build_description`."""
        return ["keywords"]

    def check_following(self, value):
        """Check if the response contain the expected keywords."""
        for keyword in self._keywords:
            if not re.search(keyword, value, flags=re.IGNORECASE):
                return False
        return True


class KeywordFrequencyChecker(Instruction):
    """Check the keyword frequency."""

    def build_description(self, *, keyword=None, frequency=None, relation=None):
        """Build the instruction description.

        Args:
          keyword: A string representing a keyword that is expected in the response.
          frequency: An integer specifying the number of times `keyword` is expected
            to appear in the response.
          relation: A string in (`less than`, `at least`), defining the relational
            operator for comparison.
            Two relational comparisons are supported for now:
            if 'less than', the actual number of occurrences < frequency;
            if 'at least', the actual number of occurrences >= frequency.

        Returns:
          A string representing the instruction description.
        """
        if not keyword:
            self._keyword = instructions_util.generate_keywords(num_keywords=1)[0]
        else:
            self._keyword = keyword.strip()

        self._frequency = frequency
        if self._frequency is None or self._frequency < 0:
            self._frequency = random.randint(1, _KEYWORD_FREQUENCY)

        if relation is None:
            self._comparison_relation = random.choice(_COMPARISON_RELATION)
        elif relation not in _COMPARISON_RELATION:
            raise ValueError(
                "The supported relation for comparison must be in "
                f"{_COMPARISON_RELATION}, but {relation} is given."
            )
        else:
            self._comparison_relation = relation

        self._description_pattern = (
            "In your response, the word {keyword} should appear {relation} "
            + "{frequency} times."
        )

        return self._description_pattern.format(
            keyword=self._keyword,
            relation=self._comparison_relation,
            frequency=self._frequency,
        )

    def get_instruction_args(self):
        """Returns the keyword args of `build_description`."""
        return {
            "keyword": self._keyword,
            "frequency": self._frequency,
            "relation": self._comparison_relation,
        }

    def get_instruction_args_keys(self):
        """Returns the args keys of `build_description`."""
        return ["keyword", "frequency", "relation"]

    def check_following(self, value):
        """Checks if the response contain the keyword with required frequency."""
        actual_occurrences = len(re.findall(self._keyword, value, flags=re.IGNORECASE))

        if self._comparison_relation == _COMPARISON_RELATION[0]:
            return actual_occurrences < self._frequency
        elif self._comparison_relation == _COMPARISON_RELATION[1]:
            return actual_occurrences >= self._frequency


class NumberOfWords(Instruction):
    """Checks the number of words."""

    def build_description(self, *, num_words=None, relation=None):
        """Build the instruction description.

        Args:
          num_words: An integer specifying the number of words contained in the
            response.
          relation: A string in (`less than`, `at least`), defining the relational
            operator for comparison.
            Two relational comparisons are supported for now:
            if 'less than', the actual number of words < num_words;
            if 'at least', the actual number of words >= num_words.

        Returns:
          A string representing the instruction description.
        """

        self._num_words = num_words
        if self._num_words is None or self._num_words < 0:
            self._num_words = random.randint(
                _NUM_WORDS_LOWER_LIMIT, _NUM_WORDS_UPPER_LIMIT
            )

        if relation is None:
            self._comparison_relation = random.choice(_COMPARISON_RELATION)
        elif relation not in _COMPARISON_RELATION:
            raise ValueError(
                "The supported relation for comparison must be in "
                f"{_COMPARISON_RELATION}, but {relation} is given."
            )
        else:
            self._comparison_relation = relation

        self._description_pattern = "Answer with {relation} {num_words} words."

        return self._description_pattern.format(
            relation=self._comparison_relation, num_words=self._num_words
        )

    def get_instruction_args(self):
        """Returns the keyword args of `build_description`."""
        return {"num_words": self._num_words, "relation": self._comparison_relation}

    def get_instruction_args_keys(self):
        """Returns the args keys of `build_description`."""
        return ["num_words", "relation"]

    def check_following(self, value):
        """Checks if the response contains the expected number of words."""
        num_words = instructions_util.count_words(value)

        if self._comparison_relation == _COMPARISON_RELATION[0]:
            return num_words < self._num_words
        elif self._comparison_relation == _COMPARISON_RELATION[1]:
            return num_words >= self._num_words


class JsonFormat(Instruction):
    """Check the Json format."""

    def build_description(self):
        self._description_pattern = (
            "Entire output should be wrapped in JSON format. You can use markdown"
            " ticks such as ```."
        )
        return self._description_pattern

    def get_instruction_args(self):
        """Returns the keyword args of `build_description`."""
        return None

    def get_instruction_args_keys(self):
        """Returns the args keys of `build_description`."""
        return []

    def check_following(self, value):
        value = (
            value.strip()
            .removeprefix("```json")
            .removeprefix("```Json")
            .removeprefix("```JSON")
            .removeprefix("```")
            .removesuffix("```")
            .strip()
        )
        try:
            json.loads(value)
        except ValueError:
            return False
        return True


class ParagraphFirstWordCheck(Instruction):
    """Check the paragraph and the first word of the nth paragraph."""

    def build_description(
        self, num_paragraphs=None, nth_paragraph=None, first_word=None
    ):
        r"""Build the instruction description.

        Args:
          num_paragraphs: An integer indicating the number of paragraphs expected
            in the response. A paragraph is a subset of the string that is
            expected to be separated by '\n\n'.
          nth_paragraph: An integer indicating the paragraph number that we look at.
            Note that n starts from 1.
          first_word: A string that represent the first word of the bth paragraph.

        Returns:
          A string representing the instruction description.
        """
        self._num_paragraphs = num_paragraphs
        if self._num_paragraphs is None or self._num_paragraphs < 0:
            self._num_paragraphs = random.randint(1, _NUM_PARAGRAPHS)

        self._nth_paragraph = nth_paragraph
        if (
            self._nth_paragraph is None
            or self._nth_paragraph <= 0
            or self._nth_paragraph > self._num_paragraphs
        ):
            self._nth_paragraph = random.randint(1, self._num_paragraphs + 1)

        self._first_word = first_word
        if self._first_word is None:
            self._first_word = instructions_util.generate_keywords(num_keywords=1)[0]
        self._first_word = self._first_word.lower()

        self._description_pattern = (
            "There should be {num_paragraphs} paragraphs. "
            + "Paragraphs and only paragraphs are separated with each other by two "
            + "new lines as if it was '\\n\\n' in python. "
            + "Paragraph {nth_paragraph} must start with word {first_word}."
        )

        return self._description_pattern.format(
            num_paragraphs=self._num_paragraphs,
            nth_paragraph=self._nth_paragraph,
            first_word=self._first_word,
        )

    def get_instruction_args(self):
        """Returns the keyword args of `build_description`."""
        return {
            "num_paragraphs": self._num_paragraphs,
            "nth_paragraph": self._nth_paragraph,
            "first_word": self._first_word,
        }

    def get_instruction_args_keys(self):
        """Returns the args keys of `build_description`."""
        return ["num_paragraphs", "nth_paragraph", "first_word"]

    def check_following(self, value):
        """Checks for required number of paragraphs and correct first word.

        Args:
          value: a string representing the response. The response may contain
            paragraphs that are separated by two new lines and the first word of
            the nth paragraph will have to match a specified word.

        Returns:
          True if the number of paragraphs is the same as required and the first
          word of the specified paragraph is the same as required. Otherwise, false.
        """

        paragraphs = re.split(r"\n\n", value)
        num_paragraphs = len(paragraphs)

        for paragraph in paragraphs:
            if not paragraph.strip():
                num_paragraphs -= 1

        # check that index doesn't go out of bounds
        if self._nth_paragraph <= num_paragraphs:
            paragraph = paragraphs[self._nth_paragraph - 1].strip()
            if not paragraph:
                return False
        else:
            return False

        first_word = ""
        punctuation = {".", ",", "?", "!", "'", '"'}

        # get first word and remove punctuation
        word = paragraph.split()[0].strip()
        # TODO(jeffrey): make more complex?
        word = word.lstrip("'")
        word = word.lstrip('"')

        for letter in word:
            if letter in punctuation:
                break
            first_word += letter.lower()

        return num_paragraphs == self._num_paragraphs and first_word == self._first_word


# TODO(jeffrey) add relation - at least/at most?
class KeySentenceChecker(Instruction):
    """Check the existence of certain key sentences."""

    def build_description(self, key_sentences=None, num_sentences=None):
        """Build the instruction description.

        Args:
          key_sentences: A sequences of strings representing the key sentences that
            are expected in the response.
          num_sentences: The number of key sentences that are expected to be seen in
            the response.

        Returns:
          A string representing the instruction description.
        """

        if not key_sentences:
            # TODO(jeffrey) make a generate sentences function? wonderwords package
            self._key_sentences = set(["For now, this is fine."])
        else:
            self._key_sentences = key_sentences

        if not num_sentences:
            self._num_sentences = random.randint(1, len(self._key_sentences))
        else:
            self._num_sentences = num_sentences

        self._description_pattern = (
            "Include {num_sentences} of the following sentences {key_sentences}"
        )

        return self._description_pattern.format(
            num_sentences=self._num_sentences, key_sentences=self._key_sentences
        )

    def get_instruction_args(self):
        """Returns the keyword args of `build_description`."""
        return {
            "num_sentences": self._num_sentences,
            "key_sentences": list(self._key_sentences),
        }

    def get_instruction_args_keys(self):
        """Returns the args keys of `build_description`."""
        return ["num_sentences", "key_sentences"]

    def check_following(self, value):
        """Checks if the response contains the expected key sentences."""
        count = 0
        sentences = instructions_util.split_into_sentences(value)
        for sentence in self._key_sentences:
            if sentence in sentences:
                count += 1

        return count == self._num_sentences


class ForbiddenWords(Instruction):
    """Checks that specified words are not used in response."""

    def build_description(self, forbidden_words=None):
        """Build the instruction description.

        Args:
          forbidden_words: A sequences of strings representing words that are not
            allowed in the response.

        Returns:
          A string representing the instruction description.
        """

        if not forbidden_words:
            self._forbidden_words = instructions_util.generate_keywords(
                num_keywords=_NUM_KEYWORDS
            )
        else:
            self._forbidden_words = list(set(forbidden_words))
        self._forbidden_words = sorted(self._forbidden_words)
        self._description_pattern = (
            "Do not include keywords {forbidden_words} in the response."
        )

        return self._description_pattern.format(forbidden_words=self._forbidden_words)

    def get_instruction_args(self):
        """Returns the keyword args of `build_description`."""
        return {"forbidden_words": self._forbidden_words}

    def get_instruction_args_keys(self):
        """Returns the args keys of `build_description`."""
        return ["forbidden_words"]

    def check_following(self, value):
        """Check if the response does not contain the expected keywords."""
        for word in self._forbidden_words:
            if re.search(r"\b" + word + r"\b", value, flags=re.IGNORECASE):
                return False
        return True


class RephraseParagraph(Instruction):
    """Checks that the paragraph is rephrased."""

    def build_description(self, *, original_paragraph, low, high):
        """Builds the instruction description.

        Args:
          original_paragraph: A string presenting the original paragraph. The
            rephrases response should have between low-high words in common.
          low: An integer presenting the lower bound of similar words.
          high: An integer representing the upper bound of similar words.

        Returns:
          A string representing the instruction description.
        """
        # TODO(jeffrey) make more encompassing
        self._original_paragraph = original_paragraph
        self._low = low
        self._high = high

        self._description = (
            "Rephrase the following paragraph: "
            + "{original_paragraph}\nYour response should have "
            + "between {low} and {high} of the same words. "
            + "Words are the same if and only if all of the "
            + "letters, ignoring cases, are the same. For "
            + "example, 'run' is the same as 'Run' but different "
            + "to 'ran'."
        )

        return self._description.format(
            original_paragraph=original_paragraph, low=self._low, high=self._high
        )

    def get_instruction_args(self):
        """Returns the keyword args of `build_description`."""
        return {
            "original_paragraph": self._original_paragraph,
            "low": self._low,
            "high": self._high,
        }

    def get_instruction_args_keys(self):
        """Returns the args keys of `build_description`."""
        return ["original_paragraph", "low", "high"]

    def check_following(self, value):
        val_words = re.findall(r"\w+", value.lower())
        original_words = re.findall(r"\w+", self._original_paragraph.lower())
        similar_words = 0

        dict_val = collections.Counter(val_words)
        dict_original = collections.Counter(original_words)

        for word in dict_original:
            similar_words += min(dict_original[word], dict_val[word])

        return similar_words >= self._low and similar_words <= self._high


class TwoResponsesChecker(Instruction):
    """Check that two responses were given."""

    def build_description(self):
        """Build the instruction description."""
        self._description_pattern = (
            "Give two different responses. Responses and only responses should"
            " be separated by 6 asterisk symbols: ******."
        )
        return self._description_pattern

    def get_instruction_args(self):
        """Returns the keyword args of `build_description`."""
        return None

    def get_instruction_args_keys(self):
        """Returns the args keys of `build_description`."""
        return []

    def check_following(self, value):
        """Checks if the response has two different answers.

        Args:
          value: A string representing the response.

        Returns:
          True if two responses are detected and false otherwise.
        """
        valid_responses = list()
        responses = value.split("******")
        for index, response in enumerate(responses):
            if not response.strip():
                if index != 0 and index != len(responses) - 1:
                    return False
            else:
                valid_responses.append(response)
        return (
            len(valid_responses) == 2
            and valid_responses[0].strip() != valid_responses[1].strip()
        )


class RepeatPromptThenAnswer(Instruction):
    """Checks that Prompt is first repeated then answered."""

    def build_description(self, *, prompt_to_repeat=None):
        """Build the instruction description.

        Args:
          prompt_to_repeat: The prompt that is meant to be repeated.

        Returns:
          A string representing the instruction description.
        """
        if not prompt_to_repeat:
            raise ValueError("prompt_to_repeat must be set.")
        else:
            self._prompt_to_repeat = prompt_to_repeat
        self._description_pattern = (
            "First repeat the request word for word without change,"
            " then give your answer (1. do not say any words or characters"
            " before repeating the request; 2. the request you need to repeat"
            " does not include this sentence)"
        )
        return self._description_pattern

    def get_instruction_args(self):
        return {"prompt_to_repeat": self._prompt_to_repeat}

    def get_instruction_args_keys(self):
        """Returns the args keys of `build_description`."""
        return ["prompt_to_repeat"]

    def check_following(self, value):
        if value.strip().lower().startswith(self._prompt_to_repeat.strip().lower()):
            return True
        return False


class EndChecker(Instruction):
    """Checks that the prompt ends with a given phrase."""

    def build_description(self, *, end_phrase=None):
        """Build the instruction description.

        Args:
          end_phrase: A string representing the phrase the response should end with.

        Returns:
          A string representing the instruction description.
        """
        self._end_phrase = (
            end_phrase.strip() if isinstance(end_phrase, str) else end_phrase
        )
        if self._end_phrase is None:
            self._end_phrase = random.choice(_ENDING_OPTIONS)
        self._description_pattern = (
            "Finish your response with this exact phrase {ender}. "
            "No other words should follow this phrase."
        )
        return self._description_pattern.format(ender=self._end_phrase)

    def get_instruction_args(self):
        return {"end_phrase": self._end_phrase}

    def get_instruction_args_keys(self):
        """Returns the args keys of `build_description`."""
        return ["end_phrase"]

    def check_following(self, value):
        """Checks if the response ends with the expected phrase."""
        value = value.strip().strip('"').lower()
        self._end_phrase = self._end_phrase.strip().lower()
        return value.endswith(self._end_phrase)


class TitleChecker(Instruction):
    """Checks the response for a title."""

    def build_description(self):
        """Build the instruction description."""
        self._description_pattern = (
            "Your answer must contain a title, wrapped in double angular brackets,"
            " such as <<poem of joy>>."
        )
        return self._description_pattern

    def get_instruction_args(self):
        return None

    def get_instruction_args_keys(self):
        """Returns the args keys of `build_description`."""
        return []

    def check_following(self, value):
        """Checks if the response contains a title."""
        pattern = r"<<[^\n]+>>"
        re_pattern = re.compile(pattern)
        titles = re.findall(re_pattern, value)

        for title in titles:
            if title.lstrip("<").rstrip(">").strip():
                return True
        return False


class LetterFrequencyChecker(Instruction):
    """Checks letter frequency."""

    def build_description(self, *, letter=None, let_frequency=None, let_relation=None):
        """Build the instruction description.

        Args:
          letter: A string representing a letter that is expected in the response.
          let_frequency: An integer specifying the number of times `keyword` is
            expected to appear in the response.
          let_relation: A string in (`less than`, `at least`), defining the
            relational operator for comparison. Two relational comparisons are
            supported for now; if 'less than', the actual number of
            occurrences < frequency; if 'at least', the actual number of
            occurrences >= frequency.

        Returns:
          A string representing the instruction description.
        """
        if (
            not letter
            or len(letter) > 1
            or ord(letter.lower()) < 97
            or ord(letter.lower()) > 122
        ):
            self._letter = random.choice(list(string.ascii_letters))
        else:
            self._letter = letter.strip()
        self._letter = self._letter.lower()

        self._frequency = let_frequency
        if self._frequency is None or self._frequency < 0:
            self._frequency = random.randint(1, _LETTER_FREQUENCY)

        if let_relation is None:
            self._comparison_relation = random.choice(_COMPARISON_RELATION)
        elif let_relation not in _COMPARISON_RELATION:
            raise ValueError(
                "The supported relation for comparison must be in "
                f"{_COMPARISON_RELATION}, but {let_relation} is given."
            )
        else:
            self._comparison_relation = let_relation

        self._description_pattern = (
            "In your response, the letter {letter} should appear {let_relation}"
            " {let_frequency} times."
        )

        return self._description_pattern.format(
            letter=self._letter,
            let_frequency=self._frequency,
            let_relation=self._comparison_relation,
        )

    def get_instruction_args(self):
        """Returns the keyword args of build description."""
        return {
            "letter": self._letter,
            "let_frequency": self._frequency,
            "let_relation": self._comparison_relation,
        }

    def get_instruction_args_keys(self):
        """Returns the args keys of `build_description`."""
        return ["letter", "let_frequency", "let_relation"]

    def check_following(self, value):
        """Checks that the response contains the letter at the right frequency."""
        value = value.lower()
        letters = collections.Counter(value)

        if self._comparison_relation == _COMPARISON_RELATION[0]:
            return letters[self._letter] < self._frequency
        else:
            return letters[self._letter] >= self._frequency


class CapitalLettersEnglishChecker(Instruction):
    """Checks that the response is in english and is in all capital letters."""

    def build_description(self):
        """Build the instruction description."""
        self._description_pattern = (
            "Your entire response should be in English, and in all capital letters."
        )
        return self._description_pattern

    def get_instruction_args(self):
        return None

    def get_instruction_args_keys(self):
        """Returns the args keys of `build_description`."""
        return []

    def check_following(self, value):
        """Checks that the response is in English and in all capital letters."""
        assert isinstance(value, str)

        try:
            return value.isupper() and langdetect.detect(value) == "en"
        except langdetect.LangDetectException as e:
            # Count as instruction is followed.
            logging.error(
                "Unable to detect language for text %s due to %s", value, e
            )  # refex: disable=pytotw.037
            return True


class LowercaseLettersEnglishChecker(Instruction):
    """Checks that the response is in english and is in all lowercase letters."""

    def build_description(self):
        """Build the instruction description."""
        self._description_pattern = (
            "Your entire response should be in English, and in all lowercase"
            " letters. No capital letters are allowed."
        )
        return self._description_pattern

    def get_instruction_args(self):
        return None

    def get_instruction_args_keys(self):
        """Returns the args keys of `build_description`."""
        return []

    def check_following(self, value):
        """Checks that the response is in English and in all lowercase letters."""
        assert isinstance(value, str)

        try:
            return value.islower() and langdetect.detect(value) == "en"
        except langdetect.LangDetectException as e:
            # Count as instruction is followed.
            logging.error(
                "Unable to detect language for text %s due to %s", value, e
            )  # refex: disable=pytotw.037
            return True


class CommaChecker(Instruction):
    """Checks the response for no commas."""

    def build_description(self):
        """Build the instruction description."""
        self._description_pattern = (
            "In your entire response, refrain from the use of any commas."
        )
        return self._description_pattern

    def get_instruction_args(self):
        return None

    def get_instruction_args_keys(self):
        """Returns the args keys of `build_description`."""
        return []

    def check_following(self, value):
        """Checks that the response does not contain commas."""
        return not re.search(r"\,", value)


class CapitalWordFrequencyChecker(Instruction):
    """Checks frequency of words with all capital letters."""

    def build_description(
        self,
        capital_frequency=None,
        capital_relation=None,
    ):
        """Build the instruction description.

        Args:
          capital_frequency: An integer that represents the number of words that
            should be in all capital letters.
          capital_relation: A string that is 'at least' or 'at most' that refers to
            the frequency.

        Returns:
          A string representing the instruction description.
        """
        self._frequency = capital_frequency
        if self._frequency is None:
            self._frequency = random.randint(1, _ALL_CAPITAL_WORD_FREQUENCY)

        self._comparison_relation = capital_relation
        if capital_relation is None:
            self._comparison_relation = random.choice(_COMPARISON_RELATION)
        elif capital_relation not in _COMPARISON_RELATION:
            raise ValueError(
                "The supported relation for comparison must be in "
                f"{_COMPARISON_RELATION}, but {capital_relation} is given."
            )

        self._description_pattern = (
            "In your response, words with all capital letters should appear"
            " {relation} {frequency} times."
        )

        return self._description_pattern.format(
            frequency=self._frequency, relation=self._comparison_relation
        )

    def get_instruction_args(self):
        """Returns the keyword args of build description."""
        return {
            "capital_frequency": self._frequency,
            "capital_relation": self._comparison_relation,
        }

    def get_instruction_args_keys(self):
        """Returns the args keys of `build_description`."""
        return ["capital_frequency", "capital_relation"]

    def check_following(self, value):
        """Checks the frequency of words with all capital letters."""
        # Hyphenated words will count as one word
        words = instructions_util.nltk.word_tokenize(value)
        capital_words = [word for word in words if word.isupper()]

        capital_words = len(capital_words)

        if self._comparison_relation == _COMPARISON_RELATION[0]:
            return capital_words < self._frequency
        else:
            return capital_words >= self._frequency


class QuotationChecker(Instruction):
    """Checks response is wrapped with double quotation marks."""

    def build_description(self):
        """Build the instruction description."""
        self._description_pattern = (
            "Wrap your entire response with double quotation marks."
        )
        return self._description_pattern

    def get_instruction_args(self):
        """Returns the keyword args of build description."""
        return None

    def get_instruction_args_keys(self):
        """Returns the args keys of `build_description`."""
        return []

    def check_following(self, value):
        """Checks if the response is wrapped with double quotation marks."""
        value = value.strip()
        return len(value) > 1 and value[0] == '"' and value[-1] == '"'


# ---------------------------------------------------------------------------
# NEW IFTrain out-of-distribution constraints
# ---------------------------------------------------------------------------

class KeywordOnceChecker(Instruction):
    """Check that a keyword appears at least once in the response."""

    def build_description(self, *, keyword=None):
        if not keyword:
            self._keyword = instructions_util.generate_keywords(num_keywords=1)[0]
        else:
            self._keyword = keyword.strip()
        self._description_pattern = (
            "Include keyword {keyword} in your response."
        )
        return self._description_pattern.format(keyword=self._keyword)

    def get_instruction_args(self):
        return {"keyword": self._keyword}

    def get_instruction_args_keys(self):
        return ["keyword"]

    def check_following(self, value):
        return bool(re.search(r"\b" + re.escape(self._keyword) + r"\b", value, flags=re.IGNORECASE))


class KeywordExactCountChecker(Instruction):
    """Check that a word appears exactly N times in the response."""

    def build_description(self, *, keyword=None, count=None):
        if not keyword:
            self._keyword = instructions_util.generate_keywords(num_keywords=1)[0]
        else:
            self._keyword = keyword.strip()
        self._count = count
        if self._count is None or self._count < 1:
            self._count = random.randint(1, 5)
        self._description_pattern = (
            "In your response, the word {keyword} should appear {count} times."
        )
        return self._description_pattern.format(keyword=self._keyword, count=self._count)

    def get_instruction_args(self):
        return {"keyword": self._keyword, "count": self._count}

    def get_instruction_args_keys(self):
        return ["keyword", "count"]

    def check_following(self, value):
        occurrences = len(re.findall(r"\b" + re.escape(self._keyword) + r"\b", value, flags=re.IGNORECASE))
        return occurrences == self._count


class ExcludeWordHarderChecker(Instruction):
    """Check that a specific keyword from the instruction is not used."""

    def build_description(self, *, keyword=None):
        if not keyword:
            self._keyword = instructions_util.generate_keywords(num_keywords=1)[0]
        else:
            self._keyword = keyword.strip()
        self._description_pattern = (
            "Do not include keyword {keyword} in the response."
        )
        return self._description_pattern.format(keyword=self._keyword)

    def get_instruction_args(self):
        return {"keyword": self._keyword}

    def get_instruction_args_keys(self):
        return ["keyword"]

    def check_following(self, value):
        return not bool(re.search(r"\b" + re.escape(self._keyword) + r"\b", value, flags=re.IGNORECASE))


class LetterExactCountChecker(Instruction):
    """Check that a specific letter appears exactly N times in the response."""

    def build_description(self, *, letter=None, count=None):
        if (
            not letter
            or len(letter) > 1
            or ord(letter.lower()) < 97
            or ord(letter.lower()) > 122
        ):
            self._letter = random.choice(list(string.ascii_lowercase))
        else:
            self._letter = letter.strip().lower()
        self._count = count
        if self._count is None or self._count < 1:
            self._count = random.randint(1, _LETTER_FREQUENCY)
        self._description_pattern = (
            "In your response, the letter {letter} should appear {count} times."
        )
        return self._description_pattern.format(letter=self._letter, count=self._count)

    def get_instruction_args(self):
        return {"letter": self._letter, "count": self._count}

    def get_instruction_args_keys(self):
        return ["letter", "count"]

    def check_following(self, value):
        value = value.lower()
        letters = collections.Counter(value)
        return letters[self._letter] == self._count


class ParagraphsTwoLineBreaksChecker(Instruction):
    """Check paragraphs separated by two line breaks (\\n\\n)."""

    def build_description(self, *, num_paragraphs=None):
        self._num_paragraphs = num_paragraphs
        if self._num_paragraphs is None or self._num_paragraphs < 1:
            self._num_paragraphs = random.randint(2, _NUM_PARAGRAPHS)
        self._description_pattern = (
            "There should be {num_paragraphs} paragraphs. "
            "Paragraphs and only paragraphs are separated with each other by two line breaks."
        )
        return self._description_pattern.format(num_paragraphs=self._num_paragraphs)

    def get_instruction_args(self):
        return {"num_paragraphs": self._num_paragraphs}

    def get_instruction_args_keys(self):
        return ["num_paragraphs"]

    def check_following(self, value):
        paragraphs = re.split(r"\n\n", value)
        num_paragraphs = len([p for p in paragraphs if p.strip()])
        return num_paragraphs == self._num_paragraphs


class FirstWordSentenceChecker(Instruction):
    """Check that the first word of each sentence is a specific word."""

    def build_description(self, *, first_word=None):
        if not first_word:
            self._first_word = instructions_util.generate_keywords(num_keywords=1)[0]
        else:
            self._first_word = first_word.strip().lower()
        self._description_pattern = (
            "The first word of each sentence should be the word {first_word}."
        )
        return self._description_pattern.format(first_word=self._first_word)

    def get_instruction_args(self):
        return {"first_word": self._first_word}

    def get_instruction_args_keys(self):
        return ["first_word"]

    def check_following(self, value):
        sentences = instructions_util.split_into_sentences(value)
        if not sentences:
            return False
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            words = re.findall(r"\w+", sentence)
            if not words:
                return False
            if words[0].lower() != self._first_word.lower():
                return False
        return True


class FirstWordAnswerChecker(Instruction):
    """Check that the first word of the entire response is a specific word."""

    def build_description(self, *, first_word=None):
        if not first_word:
            self._first_word = instructions_util.generate_keywords(num_keywords=1)[0]
        else:
            self._first_word = first_word.strip().lower()
        self._description_pattern = (
            "The first word of your response should be the word {first_word}."
        )
        return self._description_pattern.format(first_word=self._first_word)

    def get_instruction_args(self):
        return {"first_word": self._first_word}

    def get_instruction_args_keys(self):
        return ["first_word"]

    def check_following(self, value):
        value = value.strip()
        words = re.findall(r"\w+", value)
        if not words:
            return False
        return words[0].lower() == self._first_word.lower()


class LastWordSentenceChecker(Instruction):
    """Check that the last word of each sentence (before punctuation) is a specific word."""

    def build_description(self, *, last_word=None):
        if not last_word:
            self._last_word = instructions_util.generate_keywords(num_keywords=1)[0]
        else:
            self._last_word = last_word.strip().lower()
        self._description_pattern = (
            "The last word of each sentence, before punctuation, should be the word {last_word}."
        )
        return self._description_pattern.format(last_word=self._last_word)

    def get_instruction_args(self):
        return {"last_word": self._last_word}

    def get_instruction_args_keys(self):
        return ["last_word"]

    def check_following(self, value):
        sentences = instructions_util.split_into_sentences(value)
        if not sentences:
            return False
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            words = re.findall(r"\w+", sentence)
            if not words:
                return False
            if words[-1].lower() != self._last_word.lower():
                return False
        return True


class LastWordAnswerChecker(Instruction):
    """Check that the last word of the entire response is a specific word."""

    def build_description(self, *, last_word=None):
        if not last_word:
            self._last_word = instructions_util.generate_keywords(num_keywords=1)[0]
        else:
            self._last_word = last_word.strip().lower()
        self._description_pattern = (
            "The last word of your response should be the word {last_word}."
        )
        return self._description_pattern.format(last_word=self._last_word)

    def get_instruction_args(self):
        return {"last_word": self._last_word}

    def get_instruction_args_keys(self):
        return ["last_word"]

    def check_following(self, value):
        value = value.strip()
        # Remove trailing punctuation to get the last word
        words = re.findall(r"\w+", value)
        if not words:
            return False
        return words[-1].lower() == self._last_word.lower()


class BigramWrappingChecker(Instruction):
    """Check that every word bigram is wrapped in double angular brackets «...»."""

    def build_description(self):
        self._description_pattern = (
            "Wrap every word bigram in double angular brackets, "
            "such as \u00abI am\u00bb \u00abat home\u00bb \u00abwith my\u00bb \u00abcute dog\u00bb."
        )
        return self._description_pattern

    def get_instruction_args(self):
        return None

    def get_instruction_args_keys(self):
        return []

    def check_following(self, value):
        """Check that the response contains bigrams wrapped in «...»."""
        # Find all bigrams wrapped in «...»
        wrapped_bigrams = re.findall(r"\u00ab[^\u00ab\u00bb]+\u00bb", value)
        if not wrapped_bigrams:
            return False
        # Each wrapped bigram should contain exactly 2 words
        for bigram in wrapped_bigrams:
            content = bigram.strip("\u00ab\u00bb").strip()
            words = content.split()
            if len(words) != 2:
                return False
        return True


class CopyingSimpleChecker(Instruction):
    """Check that the request is repeated without change and not answered."""

    def build_description(self, *, prompt_to_copy=None):
        if not prompt_to_copy:
            raise ValueError("prompt_to_copy must be set.")
        self._prompt_to_copy = prompt_to_copy
        self._description_pattern = (
            "Repeat the request without change (do not say anything before repeating "
            "the request; the request you need to repeat does not include this sentence) "
            "and do not answer the actual request!"
        )
        return self._description_pattern

    def get_instruction_args(self):
        return {"prompt_to_copy": self._prompt_to_copy}

    def get_instruction_args_keys(self):
        return ["prompt_to_copy"]

    def check_following(self, value):
        value = value.strip()
        prompt = self._prompt_to_copy.strip()
        return value.lower() == prompt.lower()


class CopyingMultipleChecker(Instruction):
    """Check that the request is repeated N times separated by 6 asterisks."""

    def build_description(self, *, prompt_to_copy=None, copy_count=None):
        if not prompt_to_copy:
            raise ValueError("prompt_to_copy must be set.")
        self._prompt_to_copy = prompt_to_copy
        self._copy_count = copy_count
        if self._copy_count is None or self._copy_count < 1:
            self._copy_count = random.randint(2, 4)
        self._description_pattern = (
            "Repeat the request without change {copy_count} times, separated by 6 asterisk symbols "
            "(do not say anything before repeating the request; the request you need to repeat "
            "does not include this sentence) and do not answer the actual request!"
        )
        return self._description_pattern.format(copy_count=self._copy_count)

    def get_instruction_args(self):
        return {"prompt_to_copy": self._prompt_to_copy, "copy_count": self._copy_count}

    def get_instruction_args_keys(self):
        return ["prompt_to_copy", "copy_count"]

    def check_following(self, value):
        parts = value.split("******")
        valid_parts = [p.strip() for p in parts if p.strip()]
        if len(valid_parts) != self._copy_count:
            return False
        prompt = self._prompt_to_copy.strip().lower()
        return all(p.lower() == prompt for p in valid_parts)


class NoDotChecker(Instruction):
    """Check that the response does not contain dots."""

    def build_description(self):
        self._description_pattern = (
            "In your entire response, refrain from the use of . (i.e. dots) as punctuation and in general."
        )
        return self._description_pattern

    def get_instruction_args(self):
        return None

    def get_instruction_args_keys(self):
        return []

    def check_following(self, value):
        return "." not in value


class NoExclamationChecker(Instruction):
    """Check that the response does not contain exclamation marks."""

    def build_description(self):
        self._description_pattern = (
            "In your entire response, refrain from the use of ! (i.e. exclamation marks) as punctuation and in general."
        )
        return self._description_pattern

    def get_instruction_args(self):
        return None

    def get_instruction_args_keys(self):
        return []

    def check_following(self, value):
        return "!" not in value


class LowercaseWordCountChecker(Instruction):
    """Check that all lowercase words appear at most N times."""

    def build_description(self, *, max_count=None):
        self._max_count = max_count
        if self._max_count is None or self._max_count < 1:
            self._max_count = random.randint(1, 10)
        self._description_pattern = (
            "In your response, all lowercase words should appear at most {max_count} times."
        )
        return self._description_pattern.format(max_count=self._max_count)

    def get_instruction_args(self):
        return {"max_count": self._max_count}

    def get_instruction_args_keys(self):
        return ["max_count"]

    def check_following(self, value):
        words = re.findall(r"\b[a-z]+\b", value)
        word_counts = collections.Counter(words)
        return all(count <= self._max_count for count in word_counts.values())


class LetterTotalCountChecker(Instruction):
    """Check that the response contains exactly N letters (or with relation)."""

    def build_description(self, *, num_letters=None, relation=None):
        self._num_letters = num_letters
        if self._num_letters is None or self._num_letters < 1:
            self._num_letters = random.randint(50, 500)
        if relation is None:
            self._relation = random.choice(_COMPARISON_RELATION)
        elif relation not in _COMPARISON_RELATION:
            raise ValueError(
                f"The supported relation must be in {_COMPARISON_RELATION}, but {relation} is given."
            )
        else:
            self._relation = relation
        self._description_pattern = (
            "Answer with {relation} {num_letters} letters."
        )
        return self._description_pattern.format(relation=self._relation, num_letters=self._num_letters)

    def get_instruction_args(self):
        return {"num_letters": self._num_letters, "relation": self._relation}

    def get_instruction_args_keys(self):
        return ["num_letters", "relation"]

    def check_following(self, value):
        letter_count = sum(1 for c in value if c.isalpha())
        if self._relation == _COMPARISON_RELATION[0]:
            return letter_count < self._num_letters
        else:
            return letter_count >= self._num_letters


class CountingCompositionChecker(Instruction):
    """Check 3 paragraphs with exactly N sentences each and M words per sentence."""

    def build_description(self, *, n_sent=None, n_words=None):
        self._n_sent = n_sent
        if self._n_sent is None or self._n_sent < 1:
            self._n_sent = random.randint(2, 5)
        self._n_words = n_words
        if self._n_words is None or self._n_words < 1:
            self._n_words = random.randint(5, 15)
        self._description_pattern = (
            "Write 3 paragraphs, delimited by the markdown divider: ***, "
            "with exactly {n_sent} sentences each, with exactly {n_words} words in each sentence."
        )
        return self._description_pattern.format(n_sent=self._n_sent, n_words=self._n_words)

    def get_instruction_args(self):
        return {"n_sent": self._n_sent, "n_words": self._n_words}

    def get_instruction_args_keys(self):
        return ["n_sent", "n_words"]

    def check_following(self, value):
        paragraphs = re.split(r"\s?\*\*\*\s?", value)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        if len(paragraphs) != 3:
            return False
        for paragraph in paragraphs:
            sentences = instructions_util.split_into_sentences(paragraph)
            sentences = [s for s in sentences if s.strip()]
            if len(sentences) != self._n_sent:
                return False
            for sentence in sentences:
                word_count = instructions_util.count_words(sentence)
                if word_count != self._n_words:
                    return False
        return True


class UniqueWordsChecker(Instruction):
    """Check that only unique words are used (no word repeated)."""

    def build_description(self):
        self._description_pattern = (
            "Only use unique words in your response, no word should be repeated!"
        )
        return self._description_pattern

    def get_instruction_args(self):
        return None

    def get_instruction_args_keys(self):
        return []

    def check_following(self, value):
        words = re.findall(r"\b\w+\b", value.lower())
        return len(words) == len(set(words))


class IncrementKeywordChecker(Instruction):
    """Check that keyword1 appears once and keyword2 appears twice."""

    def build_description(self, *, keyword1=None, keyword2=None):
        if not keyword1 or not keyword2:
            kws = instructions_util.generate_keywords(num_keywords=2)
            self._keyword1 = keyword1.strip() if keyword1 else kws[0]
            self._keyword2 = keyword2.strip() if keyword2 else kws[1]
        else:
            self._keyword1 = keyword1.strip()
            self._keyword2 = keyword2.strip()
        self._description_pattern = (
            "Include keyword {keyword1} once in your response, keyword {keyword2} twice in your response."
        )
        return self._description_pattern.format(keyword1=self._keyword1, keyword2=self._keyword2)

    def get_instruction_args(self):
        return {"keyword1": self._keyword1, "keyword2": self._keyword2}

    def get_instruction_args_keys(self):
        return ["keyword1", "keyword2"]

    def check_following(self, value):
        count1 = len(re.findall(r"\b" + re.escape(self._keyword1) + r"\b", value, flags=re.IGNORECASE))
        count2 = len(re.findall(r"\b" + re.escape(self._keyword2) + r"\b", value, flags=re.IGNORECASE))
        return count1 == 1 and count2 == 2


class PalindromeChecker(Instruction):
    """Check that the response includes a palindrome."""

    def build_description(self):
        self._description_pattern = "Include a palindrome in your response."
        return self._description_pattern

    def get_instruction_args(self):
        return None

    def get_instruction_args_keys(self):
        return []

    def check_following(self, value):
        words = re.findall(r"\b\w+\b", value.lower())
        for word in words:
            if len(word) > 1 and word == word[::-1]:
                return True
        return False


class KeywordSpecificPositionChecker(Instruction):
    """Check that a keyword appears in the Nth sentence as the Mth word."""

    def build_description(self, *, keyword=None, sentence_num=None, word_num=None):
        if not keyword:
            self._keyword = instructions_util.generate_keywords(num_keywords=1)[0]
        else:
            self._keyword = keyword.strip()
        self._sentence_num = sentence_num
        if self._sentence_num is None or self._sentence_num < 1:
            self._sentence_num = random.randint(1, 5)
        self._word_num = word_num
        if self._word_num is None or self._word_num < 1:
            self._word_num = random.randint(1, 5)
        self._description_pattern = (
            "Include keyword {keyword} in the {sentence_num}-th sentence, "
            "as the {word_num}-th word of that sentence."
        )
        return self._description_pattern.format(
            keyword=self._keyword,
            sentence_num=self._sentence_num,
            word_num=self._word_num,
        )

    def get_instruction_args(self):
        return {
            "keyword": self._keyword,
            "sentence_num": self._sentence_num,
            "word_num": self._word_num,
        }

    def get_instruction_args_keys(self):
        return ["keyword", "sentence_num", "word_num"]

    def check_following(self, value):
        sentences = instructions_util.split_into_sentences(value)
        sentences = [s for s in sentences if s.strip()]
        if len(sentences) < self._sentence_num:
            return False
        target_sentence = sentences[self._sentence_num - 1]
        words = re.findall(r"\w+", target_sentence)
        if len(words) < self._word_num:
            return False
        return words[self._word_num - 1].lower() == self._keyword.lower()


class StartEndSameWordChecker(Instruction):
    """Check that the response starts and ends with the same word."""

    def build_description(self):
        self._description_pattern = (
            "Start and end your response with the same word "
            "(do not write anything after the last word, not even punctuation)."
        )
        return self._description_pattern

    def get_instruction_args(self):
        return None

    def get_instruction_args_keys(self):
        return []

    def check_following(self, value):
        value = value.strip()
        words = re.findall(r"\w+", value)
        if len(words) < 2:
            return False
        return words[0].lower() == words[-1].lower()


class RepeatPhraseChecker(Instruction):
    """Check that a phrase is repeated N times with one word replaced each time."""

    def build_description(self, *, phrase=None, repeat_count=None):
        if not phrase:
            kws = instructions_util.generate_keywords(num_keywords=3)
            self._phrase = " ".join(kws)
        else:
            self._phrase = phrase.strip()
        self._repeat_count = repeat_count
        if self._repeat_count is None or self._repeat_count < 2:
            self._repeat_count = random.randint(2, 4)
        self._description_pattern = (
            "Repeat the phrase \"{phrase}\" exactly {repeat_count} times, "
            "transforming it slightly each time by replacing one word."
        )
        return self._description_pattern.format(phrase=self._phrase, repeat_count=self._repeat_count)

    def get_instruction_args(self):
        return {"phrase": self._phrase, "repeat_count": self._repeat_count}

    def get_instruction_args_keys(self):
        return ["phrase", "repeat_count"]

    def check_following(self, value):
        """Check that the phrase (with one word replaced) appears repeat_count times."""
        phrase_words = self._phrase.lower().split()
        n = len(phrase_words)
        if n == 0:
            return False
        # Find all n-grams in the response
        value_words = re.findall(r"\w+", value.lower())
        count = 0
        for i in range(len(value_words) - n + 1):
            ngram = value_words[i:i + n]
            # Count differences
            diffs = sum(1 for a, b in zip(ngram, phrase_words) if a != b)
            if diffs <= 1:
                count += 1
        return count == self._repeat_count


class NoAdjacentConsecutiveLettersChecker(Instruction):
    """Check that no two adjacent words start with consecutive letters of the alphabet."""

    def build_description(self):
        self._description_pattern = (
            "No two adjacent words can start with consecutive letters of the alphabet."
        )
        return self._description_pattern

    def get_instruction_args(self):
        return None

    def get_instruction_args_keys(self):
        return []

    def check_following(self, value):
        words = re.findall(r"\b[a-zA-Z]\w*\b", value)
        for i in range(len(words) - 1):
            c1 = words[i][0].lower()
            c2 = words[i + 1][0].lower()
            if abs(ord(c1) - ord(c2)) == 1:
                return False
        return True


class SquareBracketsWordChecker(Instruction):
    """Check that every word in the response is enclosed within square brackets."""

    def build_description(self):
        self._description_pattern = (
            "Enclose every word in your response within square brackets."
        )
        return self._description_pattern

    def get_instruction_args(self):
        return None

    def get_instruction_args_keys(self):
        return []

    def check_following(self, value):
        # Find all tokens that look like words (not already in brackets)
        # Check that every word-like token is inside [...]
        # Strategy: find all words not inside brackets
        # Remove all bracketed content
        without_brackets = re.sub(r"\[[^\[\]]*\]", "", value)
        # After removing bracketed content, there should be no standalone words left
        remaining_words = re.findall(r"\b[a-zA-Z]+\b", without_brackets)
        return len(remaining_words) == 0


class SentenceHyphensChecker(Instruction):
    """Check that all sentences are connected using hyphens with no spaces between them."""

    def build_description(self):
        self._description_pattern = (
            "All sentences must be connected using hyphens, with no spaces between them."
        )
        return self._description_pattern

    def get_instruction_args(self):
        return None

    def get_instruction_args_keys(self):
        return []

    def check_following(self, value):
        value = value.strip()
        # Check that the response contains hyphens connecting sentences
        # and no spaces around hyphens used as sentence connectors
        if not value:
            return False
        # The response should not contain ". " (sentence-ending space) patterns
        # but should contain "-" connecting sentences
        # Simple check: no spaces around sentence-connecting hyphens
        # and the response uses hyphens as connectors
        has_hyphen_connector = bool(re.search(r"\w-\w", value))
        has_sentence_space = bool(re.search(r"[.!?]\s+[A-Z]", value))
        return has_hyphen_connector and not has_sentence_space


class CopyInstructionChecker(Instruction):
    """Check that the instruction is copied verbatim without following it."""

    def build_description(self, *, instruction_to_copy=None):
        if not instruction_to_copy:
            raise ValueError("instruction_to_copy must be set.")
        self._instruction_to_copy = instruction_to_copy
        self._description_pattern = (
            "Copy this instruction verbatim, do not follow the instruction, "
            "only copy it into the output (do not include this instruction sentence!)."
        )
        return self._description_pattern

    def get_instruction_args(self):
        return {"instruction_to_copy": self._instruction_to_copy}

    def get_instruction_args_keys(self):
        return ["instruction_to_copy"]

    def check_following(self, value):
        value = value.strip()
        instruction = self._instruction_to_copy.strip()
        return value.lower() == instruction.lower()


class CopySpanIndexChecker(Instruction):
    """Check that the span of words between character indices n_start and n_end is copied."""

    def build_description(self, *, source_text=None, n_start=None, n_end=None):
        if not source_text:
            raise ValueError("source_text must be set.")
        self._source_text = source_text
        self._n_start = n_start if n_start is not None else 0
        self._n_end = n_end if n_end is not None else min(len(source_text), 50)
        self._expected_span = source_text[self._n_start:self._n_end + 1]
        self._description_pattern = (
            "Copy the span of words that lies between (and including) index {n_start} and {n_end}, "
            "the indices are character indices!"
        )
        return self._description_pattern.format(n_start=self._n_start, n_end=self._n_end)

    def get_instruction_args(self):
        return {
            "source_text": self._source_text,
            "n_start": self._n_start,
            "n_end": self._n_end,
        }

    def get_instruction_args_keys(self):
        return ["source_text", "n_start", "n_end"]

    def check_following(self, value):
        return self._expected_span.strip() in value
