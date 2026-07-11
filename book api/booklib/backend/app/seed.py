from .database import SessionLocal, engine, Base
from . import models
from .security import hash_password

DUMMY_BOOKS = [
    dict(isbn="9781491946008", title="Fluent Python", author="Luciano Ramalho",
         category="Programming", price=1999.0, rating=4.7, total_copies=4,
         description="A deep dive into writing idiomatic, effective Python."),
    dict(isbn="9780132350884", title="Clean Code", author="Robert C. Martin",
         category="Programming", price=1499.0, rating=4.4, total_copies=3,
         description="A handbook of agile software craftsmanship."),
    dict(isbn="9780135957059", title="The Pragmatic Programmer", author="David Thomas & Andrew Hunt",
         category="Programming", price=1799.0, rating=4.6, total_copies=3,
         description="Classic, timeless advice for becoming a better programmer."),
    dict(isbn="9781593279288", title="Python Crash Course", author="Eric Matthes",
         category="Programming", price=1299.0, rating=4.5, total_copies=5,
         description="A fast-paced, hands-on introduction to Python programming."),
    dict(isbn="9781593275990", title="Automate the Boring Stuff with Python", author="Al Sweigart",
         category="Programming", price=999.0, rating=4.6, total_copies=4,
         description="Practical programming for total beginners."),
    dict(isbn="9780262046305", title="Introduction to Algorithms", author="Cormen, Leiserson, Rivest & Stein",
         category="Computer Science", price=3499.0, rating=4.5, total_copies=2,
         description="The definitive, comprehensive reference on algorithms."),
    dict(isbn="9780201633610", title="Design Patterns", author="Gamma, Helm, Johnson & Vlissides",
         category="Computer Science", price=2299.0, rating=4.3, total_copies=2,
         description="Elements of reusable object-oriented software, the original Gang of Four book."),
    dict(isbn="9781455586691", title="Deep Work", author="Cal Newport",
         category="Self Help", price=899.0, rating=4.4, total_copies=4,
         description="Rules for focused success in a distracted world."),
    dict(isbn="9780735211292", title="Atomic Habits", author="James Clear",
         category="Self Help", price=799.0, rating=4.8, total_copies=6,
         description="An easy and proven way to build good habits and break bad ones."),
    dict(isbn="9780062316097", title="Sapiens", author="Yuval Noah Harari",
         category="History", price=899.0, rating=4.7, total_copies=3,
         description="A brief history of humankind."),
]


def cover_url(isbn: str) -> str:
    return f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(models.Book).count() == 0:
            for b in DUMMY_BOOKS:
                db.add(models.Book(image_url=cover_url(b["isbn"]), available_copies=b["total_copies"], **b))
            print(f"Seeded {len(DUMMY_BOOKS)} books.")

        if db.query(models.Member).filter(models.Member.email == "admin@library.local").first() is None:
            admin = models.Member(
                member_code="M0000",
                name="Library Admin",
                email="admin@library.local",
                phone="9999999999",
                role=models.Role.admin,
                password_hash=hash_password("admin123"),
            )
            db.add(admin)
            print("Seeded default admin -> admin@library.local / admin123")

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run()
