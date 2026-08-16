from betman_voice.services.text_normalizer import normalize_racing_text


def test_normalizes_race_numbers_money_acronyms_and_ordinals():
    text = normalize_racing_text("Murray Bridge R4: NZB runner at $3.20. Race 5 ran 1st/2nd/3rd.")

    assert "Race four" in text
    assert "Race five" in text
    assert "three dollars twenty" in text
    assert "N Z B" in text
    assert "first, second, third" in text


def test_polishes_content_pre_normalized_price_digits():
    text = normalize_racing_text("Odds are 3 dollars 20 and Race 4 is live.")

    assert "three dollars twenty" in text
    assert "Race four" in text


def test_normalizes_racing_form_tokens_without_breaking_obvious_initials():
    text = normalize_racing_text("Form x231P. P is a pulled-up run. Jockey P J Liston.")

    assert "Form reads spell, second, third, first, pulled up" in text
    assert "pulled up is a pulled up run" in text
    assert "P J Liston" in text


def test_normalizes_odds_movements_with_pauses():
    text = normalize_racing_text("Esticon R2 drift 36.20 -> 126.00 | NZB Sale point")

    assert "Esticon Race two drifted from thirty six dollars twenty out to one hundred twenty six dollars" in text
    assert ". N Z B Sale point" in text


def test_shortens_long_robotic_sentences():
    source = " ".join(["market"] * 35)
    text = normalize_racing_text(source, max_sentence_words=12)

    assert ". " in text
    assert max(len(part.split()) for part in text.split(". ")) <= 12
