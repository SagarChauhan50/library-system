# ==========================================
# ROUTE: RETURN BOOK ACTION
# ==========================================
@app.route('/return/<int:transaction_id>')
def return_book(transaction_id):
    if 'user_id' not in session:
        return redirect(url_for('home'))
        
    user_id = session['user_id']
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        # Verify the transaction belongs to the logged-in user and get the book_id
        cursor.execute("SELECT book_id FROM transactions WHERE id = ? AND user_id = ?", (transaction_id, user_id))
        transaction = cursor.fetchone()
        
        if transaction:
            book_id = transaction[0]
            
            # Increase the available copies back by 1
            conn.execute("UPDATE books SET available_copies = available_copies + 1 WHERE id = ?", (book_id,))
            
            # Delete the transaction record since the book has been returned
            conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
            conn.commit()
            
    return redirect(url_for('dashboard'))
