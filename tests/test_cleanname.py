# encoding: utf-8

from typing import Optional

import pytest

from cleanco import basename, clean


def test_deterministic_terms(monkeypatch):
   """prepare_default_terms should always return the same list (even for different ordering in get_unique_terms)"""
   with monkeypatch.context() as m:
      mock_terms = ["aaa", "bbb", "ccc"]
      m.setattr(clean, "get_unique_terms", lambda _: mock_terms)
      res1 = clean.prepare_default_terms()
      m.setattr(clean, "get_unique_terms", lambda _: reversed(mock_terms))
      res2 = clean.prepare_default_terms()
      assert res1 == res2


# Tests that demonstrate stuff is stripped away
basic_cleanup_tests = {
    ("name w/ suffix", "Hello World Oy"),
    ("name w/ ', ltd.'", "Hello World, ltd."),
    ("name w/ ws suffix ws", "Hello    World ltd"),
    ("name w/ suffix ws", "Hello World ltd "),
    ("name w/ suffix dot ws", "Hello World ltd. "),
    ("name w/ ws suffix dot ws", " Hello World "),
    ("name w/ suffix including accents and whitespace", "Hello World S.à r.l.")
}


@pytest.mark.parametrize("testname, variation", basic_cleanup_tests)
def test_basic_cleanups(testname, variation):
    assert basename(variation) == "Hello World", "cleanup of %s failed" % testname


multi_cleanup_tests = {
    ("name + suffix", "Hello World Oy"),
    ("name + country", "Hello World Finland"),
    ("name + suffix (without punct)", "Hello World sro"),
    ("prefix + name", "Oy Hello World"),
    ("prefix + name + suffix", "Oy Hello World Ab"),
    ("name w/ term in middle", "Hello Oy World"),
    ("name w/ complex term in middle", "Hello pty ltd World"),
    ("name w/ mid + suffix", "Hello Oy World Ab")
}


@pytest.mark.parametrize("testname, variation", multi_cleanup_tests)
def test_multi_type_cleanups(testname, variation):
    result = basename(variation, prefix=True, suffix=True, middle=True)
    assert result == "Hello World", "cleanup of %s failed" % testname


# Tests that demonstrate basename can be run twice effectively
double_cleanup_tests = {
    ("name + two prefix", "Ab Oy Hello World"),
    ("name + two suffix", "Hello World Ab Oy"),
    ("name + two in middle", "Hello Ab Oy World"),
    ("name + suffix + country + suffix", "Hello World Oy Finland Co Ltd"),
    ("name + suffix + (country) + suffix", "Hello World Oy (Finland) Co Ltd")
}


@pytest.mark.parametrize("testname, variation", double_cleanup_tests)
def test_double_cleanups(testname, variation):
    assert basename(variation, prefix=True, suffix=True, middle=True) == "Hello World", "cleanup of %s failed" % testname


# Tests that demonstrate organization name is kept intact
preserving_cleanup_tests = {
    ("name with comma", "Hello, World, ltd.", "Hello, World"),
    ("name with dot", "Hello. World, Oy", "Hello. World")
}


@pytest.mark.parametrize("testname, variation, expected", preserving_cleanup_tests)
def test_preserving_cleanups(testname, variation, expected):
    assert basename(variation) == expected, "preserving cleanup of %s failed" % testname


unicode_umlaut_tests = {
    ("name with umlaut in end", "Säätämö Oy", "Säätämö"),
    ("name with umlauts & comma", "Säätämö, Oy", "Säätämö"),
    ("name with no ending umlaut", "Säätämo Oy", "Säätämo"),
    ("name with beginning umlaut", "Äätämo Oy", "Äätämo"),
    ("name with just umlauts", "Äätämö", "Äätämö"),
    ("cyrillic name", "ОАО Новороссийский морской торговый порт", "Новороссийский морской торговый порт")

}


@pytest.mark.parametrize("testname, variation, expected", unicode_umlaut_tests)
def test_with_unicode_umlauted_name(testname, variation, expected):
    assert basename(variation, prefix=True) == expected, "preserving cleanup of %s failed" % testname


terms_with_accents_tests = {
    ("term with ł correct spelling", "Łoś spółka z o.o", "Łoś"),
    ("term with ł incorrect spelling", "Łoś spolka z o.o", "Łoś"),
}

@pytest.mark.parametrize("testname, variation, expected", terms_with_accents_tests)
def test_terms_with_accents(testname, variation, expected):
    assert basename(variation, suffix=True) == expected, "preserving cleanup of %s failed" % testname


various_company_names = [
   ("FI", "Oy Grundfos Pumput Ab", "Grundfos Pumput"),
   ("FI", "Suomen Euromaster Oy", "Suomen Euromaster"),
   ("FI", "TL Trans Oy", "TL Trans"),
   ("FI", "Tmi Siivouspalvelu Myrberg", "Siivouspalvelu Myrberg"),
   ("FI", "Testcompany Oy Ltd", "Testcompany"),
   ("FI", "EV Finland Oy", "EV"),
   ("SE", "EV Finland Oy", "EV Finland Oy"),
   ("SE", "A Tavola AB", "A Tavola"),
   ("SE", "Skultuna Reklam of Sweden", "Skultuna Reklam of Sweden"),
   ("NO", "Myklebust Eigedomsselskap AS", "Myklebust Eigedomsselskap"),
   ("NO", "Ab Invest I AS", "Invest I"),
   ("NO", "NLM NAAN ANS", "NLM NAAN"),
   ("US", "BOSCO'S AUTOMOTIVE INC", "BOSCO'S AUTOMOTIVE"),
   ("US", "BOA Financial Consulting LLC", "BOA Financial Consulting"),
   ("US", "Proper Pie Co., LLC", "Proper Pie"),
   (None, "B&C ENTERPRISES, LLC", "B&C ENTERPRISES"),
   (None, "MAX 99P LTD", "MAX 99P"),
   (None, "Juniper Holdings S.à r.l.", "Juniper Holdings"),
]

@pytest.mark.parametrize("country, input_name, expected", various_company_names)
def test_problematic_cases(country: Optional[str], input_name: str, expected: str):
   cleaned_name = basename(input_name, prefix=True, country=country)
   assert cleaned_name == expected, f"{input_name} got cleaned up to {cleaned_name} instead of {expected}"
