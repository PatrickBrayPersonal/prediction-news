from prediction_news.keywords import extract_keywords


def test_strips_stop_words():
    result = extract_keywords(
        "Will Gavin Newsom become President of the United States before 2045?"
    )
    assert "will" not in result
    assert "the" not in result
    assert "of" not in result
    assert "before" not in result


def test_keeps_meaningful_words():
    result = extract_keywords(
        "Will Gavin Newsom become President of the United States before 2045?"
    )
    assert "gavin" in result
    assert "newsom" in result
    assert "president" in result
    assert "united" in result
    assert "states" in result
    assert "2045" in result


def test_appends_yes_sub_title_words():
    result = extract_keywords("Who will the next Pope be?", "Peter Erdo")
    assert "pope" in result
    assert "peter" in result
    assert "erdo" in result


def test_no_duplicate_from_yes_sub_title():
    result = extract_keywords("Will Gavin Newsom become President?", "Gavin Newsom")
    assert result.count("gavin") == 1
    assert result.count("newsom") == 1


def test_empty_yes_sub_title():
    result = extract_keywords("Will Democrats win the election?")
    assert "democrats" in result
    assert "win" in result
    assert "election" in result
    assert "will" not in result
    assert "the" not in result


def test_strips_punctuation():
    result = extract_keywords("Will the world pass 2°C?")
    assert all("?" not in kw for kw in result)


def test_empty_headline_returns_empty():
    assert extract_keywords("") == []


def test_yes_sub_title_stop_words_not_added():
    result = extract_keywords("Will Democrats win?", "will the")
    assert result.count("will") == 0
    assert result.count("the") == 0
