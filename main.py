# ==============================
# 📚 PRODUCTION LIBRARY API
# ==============================

from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from pydantic import BaseModel
from datetime import datetime, timedelta



DATABASE_URL = "sqlite:///./library.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()



class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    author = Column(String)
    category = Column(String)
    available = Column(Boolean, default=True)

class Borrow(Base):
    __tablename__ = "borrowed_books"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    book_id = Column(Integer, ForeignKey("books.id"))
    due_date = Column(DateTime)


Base.metadata.create_all(bind=engine)



app = FastAPI(title="Limkokwing Library")



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



class UserCreate(BaseModel):
    name: str

class BookCreate(BaseModel):
    title: str
    author: str
    category: str

class BorrowRequest(BaseModel):
    user_id: int
    book_id: int



@app.post("/users")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    new_user = User(name=user.name)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()



@app.post("/books")
def create_book(book: BookCreate, db: Session = Depends(get_db)):
    new_book = Book(**book.dict())
    db.add(new_book)
    db.commit()
    db.refresh(new_book)
    return new_book

@app.get("/books")
def get_books(db: Session = Depends(get_db)):
    return db.query(Book).all()



@app.post("/borrow")
def borrow_book(req: BorrowRequest, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.id == req.user_id).first()
    book = db.query(Book).filter(Book.id == req.book_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if not book.available:
        raise HTTPException(status_code=400, detail="Book not available")

    book.available = False

    borrow = Borrow(
        user_id=user.id,
        book_id=book.id,
        due_date=datetime.now() + timedelta(days=7)
    )

    db.add(borrow)
    db.commit()

    return {
        "message": "Book borrowed successfully",
        "user": user.name,
        "book": book.title,
        "due_date": borrow.due_date
    }



@app.post("/return")
def return_book(req: BorrowRequest, db: Session = Depends(get_db)):

    borrow = db.query(Borrow).filter(
        Borrow.user_id == req.user_id,
        Borrow.book_id == req.book_id
    ).first()

    if not borrow:
        raise HTTPException(status_code=400, detail="Borrow record not found")

    book = db.query(Book).filter(Book.id == req.book_id).first()

    days_late = (datetime.now() - borrow.due_date).days
    fine = max(0, days_late * 2)

    book.available = True

    db.delete(borrow)
    db.commit()

    return {
        "message": "Book returned successfully",
        "fine": fine
    }





@app.get("/overdue/{user_id}")
def get_overdue(user_id: int, db: Session = Depends(get_db)):

    borrows = db.query(Borrow).filter(Borrow.user_id == user_id).all()

    result = []

    for b in borrows:
        days_late = (datetime.now() - b.due_date).days
        if days_late > 0:
            book = db.query(Book).filter(Book.id == b.book_id).first()

            result.append({
                "book": book.title,
                "days_overdue": days_late,
                "fine": days_late * 2
            })

    return {"overdue_books": result}
