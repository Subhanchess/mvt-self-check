import unittest

from check import extract_candidate


HTML_WITH_MAIN = """
<html>
  <body>
    <main>
      <div class="content">
        Başvuru son tarihi 31.12.2024
      </div>
    </main>
    <section>
      Diğer bilgi 01.01.2024
    </section>
  </body>
</html>
"""


class ExtractCandidateTests(unittest.TestCase):
    def test_snapshot_mode_allows_plain_tag_selector(self):
        result = extract_candidate(HTML_WITH_MAIN, "main", snapshot_mode=True)
        self.assertEqual(result, "31.12.2024")

    def test_plain_hint_still_matches_text_in_regular_mode(self):
        result = extract_candidate(HTML_WITH_MAIN, "deadline")
        self.assertEqual(result, "31.12.2024")


if __name__ == "__main__":
    unittest.main()
