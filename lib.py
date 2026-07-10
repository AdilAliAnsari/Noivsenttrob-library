import re
import time
import json
import functools
import threading
from datetime import datetime, date


def log_call(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"[LOG] calling {func.__name__}{args[1:]}")
        result = func(*args, **kwargs)
        print(f"[LOG] {func.__name__} -> {result}")
        return result

    return wrapper


class Book:
    def __init__(self, title, author, isbn):
        self.title = title
        self.author = author
        self.isbn = isbn
        self.is_issued = False
        self.issued_to = None
        self.issued_date = None

    def __str__(self):
        status = f"Issued to {self.issued_to}" if self.is_issued else "Available"
        return f"Book: {self.title} by {self.author} (ISBN: {self.isbn}) [{status}]"

    def __lt__(self, other):
        return self.title.lower() < other.title.lower()


class Member:
    EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}$")
    PHONE_RE = re.compile(r"^\d{10}$")

    def __init__(self, name, member_id, email, phone):
        if not self.EMAIL_RE.match(email):
            raise ValueError(f"Invalid email address: {email}")
        if not self.PHONE_RE.match(phone):
            raise ValueError(f"Invalid phone number: {phone}")
        self.name = name
        self.member_id = member_id
        self.email = email
        self.phone = phone
        self.max_books = 2
        self.books_held = []

    def __str__(self):
        return f"{self.name} ({self.member_id}) - {self.__class__.__name__}"


class Student(Member):
    def __init__(self, name, member_id, email, phone, roll_no):
        super().__init__(name, member_id, email, phone)
        self.roll_no = roll_no
        self.max_books = 3


class Faculty(Member):
    def __init__(self, name, member_id, email, phone, department):
        super().__init__(name, member_id, email, phone)
        self.department = department
        self.max_books = 10


class Fine:
    RATE_PER_DAY = 1.0

    def calculate(self, days_late):
        if days_late <= 0:
            return 0.0
        return days_late * self.RATE_PER_DAY


class StudentFine(Fine):
    RATE_PER_DAY = 0.5


class FacultyFine(Fine):
    def calculate(self, days_late):
        return 0.0


def get_fine_calculator(member):
    if isinstance(member, Student):
        return StudentFine()
    if isinstance(member, Faculty):
        return FacultyFine()
    return Fine()


class Library:
    def __init__(self):
        self.books = {}
        self.members = {}

    def add_book(self, book: Book):
        self.books[book.isbn] = book
        print(f"Book added: {book}")

    def register_member(self, member: Member):
        self.members[member.member_id] = member
        print(f"Member registered: {member}")

    @log_call
    def issue_book(self, isbn, member_id):
        book = self.books.get(isbn)
        member = self.members.get(member_id)
        if not book:
            return "Error: Book not found"
        if not member:
            return "Error: Member not found"
        if book.is_issued:
            return f"Error: Book '{book.title}' is already issued"
        if len(member.books_held) >= member.max_books:
            return f"Error: {member.name} has reached the max limit of {member.max_books} books."
        book.is_issued = True
        book.issued_to = member.member_id
        book.issued_date = date.today()
        member.books_held.append(isbn)
        return f"Book '{book.title}' issued to {member.name}."

    @log_call
    def return_book(self, isbn, days_late=0):
        book = self.books.get(isbn)
        if not book or not book.is_issued:
            return "Error: Book not found or was not issued."
        member = self.members.get(book.issued_to)
        fine_calculator = get_fine_calculator(member) if member else Fine()
        fine_amount = fine_calculator.calculate(days_late)
        if member and isbn in member.books_held:
            member.books_held.remove(isbn)
        book.is_issued = False
        book.issued_to = None
        book.issued_date = None
        if fine_amount > 0:
            return f"'{book.title}' returned. Fine due: Rs.{fine_amount:.2f}"
        return f"'{book.title}' returned. No fine."

    def issued_titles(self):
        return [b.title for b in self.books.values() if b.is_issued]

    def isbn_to_title_map(self):
        return {isbn: b.title for isbn, b in self.books.items()}

    def member_books_map(self):
        return {m.member_id: list(m.books_held) for m in self.members.values() if m.books_held}

    def unique_authors(self):
        return {b.author for b in self.books.values()}

    def overdue_batches(self, max_days_allowed=14, batch_size=2):
        overdue = [
            b for b in self.books.values()
            if b.is_issued and (date.today() - b.issued_date).days > max_days_allowed
        ]
        for i in range(0, len(overdue), batch_size):
            yield overdue[i:i + batch_size]

    def search_by_title(self, pattern):
        regex = re.compile(pattern, re.IGNORECASE)
        return [b for b in self.books.values() if regex.search(b.title)]

    def send_overdue_reminders(self):
        overdue_books = [b for b in self.books.values() if b.is_issued]

        def notify(member_id, book_title):
            time.sleep(1)   # simulate network/email delay
            member = self.members.get(member_id)
            name = member.name if member else member_id
            print(f"  -> Reminder sent to {name} about '{book_title}'")

        threads = [
            threading.Thread(target=notify, args=(b.issued_to, b.title))
            for b in overdue_books
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        print("All reminders sent.")

    def save_state(self, filepath="library_state.json"):
        data = {
            "books": [
                {
                    "title": b.title, "author": b.author, "isbn": b.isbn,
                    "is_issued": b.is_issued, "issued_to": b.issued_to,
                    "issued_date": b.issued_date.isoformat() if b.issued_date else None,
                }
                for b in self.books.values()
            ],
            "members": [
                {
                    "type": m.__class__.__name__, "name": m.name, "member_id": m.member_id,
                    "email": m.email, "phone": m.phone, "books_held": m.books_held,
                    "roll_no": getattr(m, "roll_no", None),
                    "department": getattr(m, "department", None),
                }
                for m in self.members.values()
            ],
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        print(f"State saved to {filepath}")

    def load_state(self, filepath="library_state.json"):
        with open(filepath, "r") as f:
            data = json.load(f)

        self.books.clear()
        self.members.clear()

        for bd in data.get("books", []):
            book = Book(bd["title"], bd["author"], bd["isbn"])
            book.is_issued = bd.get("is_issued", False)
            book.issued_to = bd.get("issued_to")
            book.issued_date = datetime.fromisoformat(bd["issued_date"]).date() if bd.get("issued_date") else None
            self.books[book.isbn] = book

        for md in data.get("members", []):
            if md.get("type") == "Student":
                member = Student(md["name"], md["member_id"], md["email"], md["phone"], md.get("roll_no"))
            elif md.get("type") == "Faculty":
                member = Faculty(md["name"], md["member_id"], md["email"], md["phone"], md.get("department"))
            else:
                member = Member(md["name"], md["member_id"], md["email"], md["phone"])
            member.books_held = md.get("books_held", [])
            self.members[member.member_id] = member

        print(f"State loaded from {filepath}")


def main():
    library = Library()

    # Add books
    library.add_book(Book("Fluent Python", "Luciano Ramalho", "ISBN-001"))
    library.add_book(Book("Clean Code", "Robert Martin", "ISBN-002"))
    library.add_book(Book("Python Tricks", "Dan Bader", "ISBN-003"))
    library.add_book(Book("Automate the Boring Stuff", "Al Sweigart", "ISBN-004"))

    # Register members (regex validation happens inside Member.__init__)
    library.register_member(Student("Anand", "M001", "anand@example.com", "9876543210", roll_no="R101"))
    library.register_member(Faculty("Divya", "M002", "divya@example.com", "9123456789", department="CSE"))

    print("\n--- Issuing books ---")
    print(library.issue_book("ISBN-001", "M001"))
    print(library.issue_book("ISBN-002", "M001"))
    print(library.issue_book("ISBN-003", "M002"))

    print("\n--- Reports (comprehensions) ---")
    print("Issued titles:", library.issued_titles())
    print("ISBN -> Title map:", library.isbn_to_title_map())
    print("Member -> Books map:", library.member_books_map())
    print("Unique authors:", library.unique_authors())

    print("\n--- Sorted book list (uses Book.__lt__) ---")
    for b in sorted(library.books.values()):
        print(" ", b)

    print("\n--- Search by title (regex) ---")
    for b in library.search_by_title(r"python"):
        print(" ", b)

    print("\n--- Returning a book with a late fee ---")
    print(library.return_book("ISBN-001", days_late=5))   # Student -> discounted fine
    print(library.return_book("ISBN-003", days_late=5))   # Faculty -> exempt

    print("\n--- Sending reminders to members with books still out (multithreaded) ---")
    library.send_overdue_reminders()

    print("\n--- Saving and reloading state (file handling) ---")
    library.save_state("library_state.json")
    reloaded = Library()
    reloaded.load_state("library_state.json")
    print("Reloaded books:", [str(b) for b in reloaded.books.values()])


if __name__ == "__main__":
    main()
