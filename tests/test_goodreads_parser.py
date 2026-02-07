from shelflife.services.goodreads import parse_goodreads_csv

SAMPLE_CSV = '''\
Book Id,Title,Author,Author l-f,Additional Authors,ISBN,ISBN13,My Rating,Average Rating,Publisher,Binding,Number of Pages,Year Published,Original Publication Year,Date Read,Date Added,Bookshelves,Bookshelves with positions,Exclusive Shelf,My Review,Spoiler,Private Notes,Read Count,Owned Copies
12345,The Great Gatsby,F. Scott Fitzgerald,"Fitzgerald, F. Scott",,"=""0743273567""","=""9780743273565""",5,3.93,Scribner,Paperback,180,2004,1925,2024/01/15,2023/12/01,"classics, fiction",,read,Amazing book.,,,1,0
67890,Dune,Frank Herbert,"Herbert, Frank",,"=""0441172717""","=""9780441172719""",0,4.25,Ace Books,Paperback,688,2005,1965,,2024/03/10,sci-fi,,currently-reading,,,,0,1
'''


def test_parse_csv_basic():
    rows = parse_goodreads_csv(SAMPLE_CSV)
    assert len(rows) == 2


def test_parse_csv_fields():
    rows = parse_goodreads_csv(SAMPLE_CSV)
    gatsby = rows[0]
    assert gatsby.goodreads_id == "12345"
    assert gatsby.title == "The Great Gatsby"
    assert gatsby.author == "F. Scott Fitzgerald"
    assert gatsby.isbn == "0743273567"
    assert gatsby.isbn13 == "9780743273565"
    assert gatsby.page_count == 180
    assert gatsby.year_published == 2004
    assert gatsby.rating == 5
    assert gatsby.review_text == "Amazing book."
    assert gatsby.exclusive_shelf == "read"


def test_parse_csv_bookshelves():
    rows = parse_goodreads_csv(SAMPLE_CSV)
    gatsby = rows[0]
    assert "classics" in gatsby.bookshelves
    assert "fiction" in gatsby.bookshelves


def test_parse_csv_no_rating():
    rows = parse_goodreads_csv(SAMPLE_CSV)
    dune = rows[1]
    assert dune.rating is None  # My Rating is 0, so parser treats as unrated


def test_parse_csv_dates():
    rows = parse_goodreads_csv(SAMPLE_CSV)
    gatsby = rows[0]
    assert gatsby.date_read is not None
    assert gatsby.date_read.year == 2024
    assert gatsby.date_read.month == 1
    dune = rows[1]
    assert dune.date_read is None
