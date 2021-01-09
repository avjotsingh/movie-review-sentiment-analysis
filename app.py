from flask import Flask, render_template, request, redirect, url_for
from utils import *
import sqlite3 as sql
import pickle
import uuid

app = Flask(__name__)

conn = sql.connect('review.db')
print("Opened database successfully")
conn.execute("""
CREATE TABLE IF NOT EXISTS imdb (
    id TEXT,
    review TEXT,
    prediction TEXT,
    feedback TEXT);
""")
conn.close()
print("Closed database successfully")

model = pickle.load(open('imdb-model', 'rb'))
vectorizer = pickle.load(open('count-vectorizer', 'rb'))

@app.route('/')
@app.route('/home', methods=['GET'])
def home():
    return render_template('home.html')

@app.route('/imdb', methods=['GET', 'POST'])
def imdb():
    if request.method == 'GET':
        return render_template('imdb.html')
    elif request.method == 'POST':
        try:
            review = request.form['review']
            if review is None:
                msg = "No review found to be processed."
                return render_template('error.html', msg=msg)
            
            processed_review = preprocess_review(review)
            review_id = str(uuid.uuid4())
            review_bag = vectorizer.transform([processed_review])
            prediction = model.predict(review_bag)[0]
            print(review_id, prediction)
            try:
                with sql.connect('review.db') as conn:
                    cur = conn.cursor()
                    arr = [review_id, review, prediction, None,]
                    print("Array len", len(arr))
                    print("Review", review)
                    print("Review len", len(review))
                    cur.execute("""
                        INSERT INTO imdb (id, review, prediction, feedback) VALUES (?, ?, ?, ?);
                        """,(review_id, review, prediction, None))
                    conn.commit()
        
                    print("Query successful")
                return redirect(f"/result/{review_id}")
            except Exception as e:
                raise Exception(e)
            finally:
                conn.close()
        except Exception as e:
            print(e)
            conn.rollback()
            msg = "There was an error in sentiment prediction."
            return render_template('error.html', msg=msg)

@app.route('/result/<review_id>', methods=['GET'])
def result(review_id):
    try:
        with sql.connect('review.db') as conn:
            conn.row_factory = sql.Row
            cur = conn.cursor()
            print("Review to fetch", review_id)
            cur.execute("""
                SELECT prediction from imdb
                WHERE id=(?);
            """,(review_id,))
            print("Query executed successfully")
            row = cur.fetchall()[0]
        return render_template('result.html', review_id=review_id, result=row['prediction'])
    except Exception as e:
        print(e)
        msg = "Result of sentiment prediction could not be fetched."
        return render_template('error.html', msg=msg)
    finally:
        conn.close()

@app.route('/feedback/<review_id>', methods=['POST'])
def feedback(review_id):
    try:
        feedback = request.form['feedback']
        if feedback is None:
            msg = "No feedback provided."
            return render_template('error.html', msg=msg)
        print(feedback)
        if feedback == "Skip":
            return redirect(url_for('home'))
        try:
            with sql.connect('review.db') as conn:
                conn.row_factory = sql.Row
                cur = conn.cursor()

                cur.execute("""
                    UPDATE imdb 
                    SET feedback=(?)
                    WHERE id=(?) 
                """, (feedback, review_id))
                conn.commit()

                return redirect(url_for('home'))
        except Exception as e:
            raise Exception(e)
        finally:
            conn.close()
    except Exception as e:
        print(e)
        conn.rollback()
        msg = "Feedback could not be stored."
        return render_template('error.html', msg=msg)

@app.route('/data')
def data():
    try:
        with sql.connect('review.db') as conn:
            conn.row_factory = sql.Row
            cur = conn.cursor()

            cur.execute("""
                SELECT * FROM imdb;
            """)

            rows = cur.fetchall()
            return render_template('data.html', rows=rows)
    except Exception as e:
        msg = "Failed to load records."
        return render_template('error.html', msg=msg)
    finally:
        conn.close()

if __name__ == '__main__':
    app.run()