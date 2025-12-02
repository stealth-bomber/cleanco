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
    ("name w/ suffix including accents and whitespace", "Hello World S.à r.l."),
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
    ("name w/ mid + suffix", "Hello Oy World Ab"),
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
    ("name + suffix + (country) + suffix", "Hello World Oy (Finland) Co Ltd"),
}


@pytest.mark.parametrize("testname, variation", double_cleanup_tests)
def test_double_cleanups(testname, variation):
    assert (
        basename(variation, prefix=True, suffix=True, middle=True) == "Hello World"
    ), "cleanup of %s failed" % testname


# Tests that demonstrate organization name is kept intact
preserving_cleanup_tests = {
    ("name with comma", "Hello, World, ltd.", "Hello, World"),
    ("name with dot", "Hello. World, Oy", "Hello. World"),
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
    (
        "cyrillic name",
        "ОАО Новороссийский морской торговый порт",
        "Новороссийский морской торговый порт",
    ),
}


@pytest.mark.parametrize("testname, variation, expected", unicode_umlaut_tests)
def test_with_unicode_umlauted_name(testname, variation, expected):
    assert basename(variation, prefix=True) == expected, (
        "preserving cleanup of %s failed" % testname
    )


terms_with_accents_tests = {
    ("term with ł correct spelling", "Łoś spółka z o.o", "Łoś"),
    ("term with ł incorrect spelling", "Łoś spolka z o.o", "Łoś"),
}


@pytest.mark.parametrize("testname, variation, expected", terms_with_accents_tests)
def test_terms_with_accents(testname, variation, expected):
    assert basename(variation, suffix=True) == expected, (
        "preserving cleanup of %s failed" % testname
    )


various_company_names = [
    ("FI", "Oy Grundfos Pumput Ab", "Grundfos Pumput"),
    ("FI", "Suomen Euromaster Oy", "Suomen Euromaster"),
    ("FI", "TL Trans Oy", "TL Trans"),
    ("FI", "Tmi Siivouspalvelu Myrberg", "Siivouspalvelu Myrberg"),
    ("FI", "Testcompany Oy Ltd", "Testcompany"),
    ("FI", "EV Finland Oy", "EV"),
    ("SE", "EV Finland Oy", "EV Finland"),
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
    assert cleaned_name == expected, (
        f"{input_name} got cleaned up to {cleaned_name} instead of {expected}"
    )


finnish_branch_tests = [
    (
        "Nordisk Kellogg Finland, Nordisk Kellogg ApS, filial i Finland",
        "Nordisk Kellogg",
    ),
    ("Ferrero Scandinavia AB, filial i Finland", "Ferrero Scandinavia"),
    ("Infineon Technologies Nordic AB, filial", "Infineon Technologies"),
    ("Amazon Web Services EMEA SARL, sivuliike Suomessa", "Amazon Web Services EMEA"),
    ("Mastercard Europe SA, sivuliike Suomessa", "Mastercard Europe"),
    ("Sony Europe B.V.,Suomen sivuliike", "Sony Europe"),
    ("Fresenius Kabi AB, sivuliike Suomessa - filial i Finland", "Fresenius Kabi"),
    ("Chubb European Group SE, sivuliike Suomessa", "Chubb European Group"),
    (
        "Samsung Semiconductor Europe GmbH, Sivuliike Helsingissä/ Helsinki Branch",
        "Samsung Semiconductor Europe",
    ),
    ("Daikin Europe N.V. Suomen Sivuliike", "Daikin Europe"),
    ("Apple Aktiebolag, filial i Finland", "Apple"),
    ("Stadium Outlet Aktiebolag filial i Finland", "Stadium Outlet"),
    ("Wallenius Wilhelmsen Ocean AS, Suomen sivuliike", "Wallenius Wilhelmsen Ocean"),
    ("Lidl Suomi Kommandiittiyhtiö", "Lidl"),
    ("Amundi Asset Management, Suomen sivuliike", "Amundi Asset Management"),
    ("Hansgrohe SE, Helsingin sivuliike", "Hansgrohe"),
    ("Mott Macdonald Limited, Suomen sivuliike", "Mott Macdonald"),
    ("TP Vision Europe B.V., Suomen sivuliike", "TP Vision Europe"),
    ("Panasonic Industry Europe GmbH, Suomen sivuliike", "Panasonic Industry Europe"),
    (
        "Deloitte Consulting & Advisory BV/SRL, sivuliike Suomessa",
        "Deloitte Consulting & Advisory",
    ),
    (
        "Yamaha Music Europe GmbH, Filial i Finland/Suomen sivuliike",
        "Yamaha Music Europe",
    ),
    ("Filialen BYGGmax AB Finland", "BYGGmax"),
    ("Arcadis Consulting (UK) Limited sivuliike Suomessa", "Arcadis Consulting"),
    ("Osuuskunta Maitosuomi", "Maitosuomi"),
    ("Aura Rakennus Länsi-Suomi Oy", "Aura Rakennus Länsi-Suomi"),
    ("Suominen Oyj", "Suominen"),
    (
        "Mitsubishi HC Capital Europe B.V., Suomi sivuliike",
        "Mitsubishi HC Capital Europe",
    ),
    ("Suomi Teline Oy", "Suomi Teline"),
    ("Suomi Camping Oy", "Suomi Camping"),
    ("OP Osuuskunta", "OP"),
    ("Metsäliitto Osuuskunta", "Metsäliitto"),
    ("Kuusamon energia- ja vesiosuuskunta", "Kuusamon energia- ja vesiosuuskunta"),
    ("Osuuskunta Meriasennus", "Meriasennus"),
    ("Enity Bank Group AB (publ), filial i Finland", "Enity Bank"),
    ("BlackRock (Netherlands) B.V., Helsingin sivuliike", "BlackRock"),
    ("Försäkringsaktiebolaget Agria (publ), filial i Finland", "Agria"),
    (
        "LG Electronics Nordic AB - filial Finland (sivuliike Suomi)",
        "LG Electronics Nordic",
    ),
    ("Suomalainen Energiaosuuskunta (SEO)", "Suomalainen Energiaosuuskunta"),
    ("DHL Freight (Finland) Oy", "DHL Freight"),
    ("Trend Micro (EMEA) Limited, Filial i Finland", "Trend Micro"),
    ("Hilti (Suomi) Oy", "Hilti"),
    ("ASI Oy Ltd (ARGUS Spectrum International)", "ASI"),
    ("Yhteismaa ry", "Yhteismaa"),
    ("Vaasan Yrittäjänaiset ry", "Vaasan Yrittäjänaiset"),
    ("Ungdomslyftet rf", "Ungdomslyftet"),
    ("Hellnäs Ungdomsförening rf", "Hellnäs Ungdomsförening"),
    ("FAKTA-säätiö sr", "FAKTA-säätiö"),
    ("Ähtärin Talonpoikaiskulttuuri säätiö sr", "Ähtärin Talonpoikaiskulttuuri säätiö"),
    ("Vihnusrinnesäätiö sr", "Vihnusrinnesäätiö"),
    ("Turo Oy:n Eläkesäätiö s.r.", "Turo Oy:n Eläkesäätiö"),
    (
        "Syöpäjärjestöjen Toimihenkilöiden Eläkesäätiö s.r.",
        "Syöpäjärjestöjen Toimihenkilöiden Eläkesäätiö",
    ),
    ("Suomen Henkikirjoittajayhdistys r.y.", "Suomen Henkikirjoittajayhdistys"),
    (
        "Suomen Harmonikkainstituutin kannatusyhdistys r.y.",
        "Suomen Harmonikkainstituutin kannatusyhdistys",
    ),
    (
        "Helsingin Seudun Reserviläispiiri ry, Helsingfors Reservistdistrikt rf",
        "Helsingin Seudun Reserviläispiiri",
    ),
    ("Suomen Lämpömittari Oy - Finska Termometer Ab", "Suomen Lämpömittari"),
    (
        "Suomen Painoväritehdas Oy - Finska Tryckfärgfabriken Ab",
        "Suomen Painoväritehdas",
    ),
    (
        "Suomen Viiriäiskoirakerho ry;Finska Wachtelhundklubben rf",
        "Suomen Viiriäiskoirakerho",
    ),
    (
        "Suomenlahden meri- ja rajavartioyhdistys ry, Finska Vikens sjö- och gränsbevakningsförening rf",
        "Suomenlahden meri- ja rajavartioyhdistys",
    ),
    (
        "Suomen Tricologian yhdistys ry Finska Tricologi förening rf",
        "Suomen Tricologian yhdistys",
    ),
    (
        "Suomen Tiedeseura r.y.;Finska Vetenskaps-Societeten r.f.",
        "Suomen Tiedeseura",
    ),
    (
        "Omakotiyhdistys Hiekkakäpy r.y. ruotsiksi Egnahemsföreningen Sandkotten r.f.",
        "Omakotiyhdistys Hiekkakäpy",
    ),
    ("Anora Group Oyj", "Anora"),
    ("Sitowise Group Oyj", "Sitowise"),
    ("Freska Group Oy", "Freska"),
    ("Posti Group Suomi", "Posti"),
    ("Lindex Group Oyj", "Lindex"),
    ("Pihla Group Oy", "Pihla"),
    ("Ab ME Group Oy Ltd", "ME Group"),
    ("Med Group Oy", "Med Group"),
    ("HL Group Oy", "HL Group"),
    ("KSPT Group Oy", "KSPT Group"),
    ("LP-Group Nummela Oy", "LP-Group Nummela"),
    ("G - J Group Oy", "G - J Group"),
    ("Keskinäinen työeläkevakuutusyhtiö Varma", "Varma"),
    ("Keskinäinen Eläkevakuutusyhtiö Ilmarinen", "Ilmarinen"),
    ("Keskinäinen Työeläkevakuutusyhtiö Elo", "Elo"),
    ("LähiTapiola Keskinäinen Vakuutusyhtiö", "LähiTapiola"),
    ("Keskinäinen Vakuutusyhtiö Turva", "Turva"),
    ("Keskinäinen Vakuutusyhtiö Fennia", "Fennia"),
    ("Valion Keskinäinen Vakuutusyhtiö", "Valion Keskinäinen Vakuutusyhtiö"),
    ("Pohjantähti Keskinäinen Vakuutusyhtiö", "Pohjantähti"),
    ("RSV Holding Oü, Suomen sivuliike", "RSV Holding"),
    ("Harjanti OÜ Suomen sivuliike", "Harjanti"),
    ("Merlingo Invest OÜ, Suomen sivuliike", "Merlingo Invest"),
    ("OÜ Mamako sivuliike Suomessa", "Mamako"),
    ("Keskinäinen Osakeyhtiö Soleil du Sud Ltd", "Soleil du Sud"),
    ("Ensiaputukku OÜ, Suomen sivuliike", "Ensiaputukku"),
    ("Hue people in Finland ry", "Hue people in Finland"),  # Country after "in" / "of"
    (
        "Suomen Kosmetologien Yhdistys - Kosmetologföreningen i Finland ry",
        "Suomen Kosmetologien Yhdistys",
    ),
    (
        "Osuuskunta Hamnskärin pienvenesatama - Andelslag Hamnskär småbåtshamn",
        "Hamnskärin pienvenesatama",
    ),
    (
        "Kiinteistö ja Rakennuspalvelu Hokkanen Oy",
        "Kiinteistö ja Rakennuspalvelu Hokkanen",
    ),
    ("Osuuskunta Meri Silta - Ocean Bridge co-op", "Meri Silta"),
    (
        "Helsingin Festivaaliorkesterin Osuuskunta",
        "Helsingin Festivaaliorkesterin Osuuskunta",
    ),  # Preceding word in genitive (ends with "n")
    # Condominium cases
    (
        "As. Oy Finnsbackankallio - Bostads Ab Finnsbackaberget",
        "Finnsbackankallio",
    ),
    ("Asunto Oy Kalannintie 37", "Kalannintie 37"),
    ("As.Oy Jyrkkärinne Helsinki", "Jyrkkärinne Helsinki"),
    (
        "Asunto Oy Sepänkylän Mesimarja - Bostads Ab Smedsby Åkerbär",
        "Sepänkylän Mesimarja",
    ),
    ("Kiinteistö Oy Jokelantörmäntie", "Jokelantörmäntie"),
    ("As. Oy Maasälväntie 10", "Maasälväntie 10"),
]


@pytest.mark.parametrize("input_name, expected", finnish_branch_tests)
def test_finnish_branch_patterns(input_name: str, expected: str):
    cleaned_name = basename(input_name, country="FI")
    assert cleaned_name == expected, (
        f"{input_name} got cleaned up to {cleaned_name} instead of {expected}"
    )
