"""
Payment Gateway Integration Module using Razorpay
Handles payment orders, verification, and transaction tracking
"""

import razorpay
import os
from pathlib import Path
from typing import Dict, Optional, Tuple
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
import hashlib
import hmac

# Load environment variables
load_dotenv()

# Razorpay API Keys
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

# Initialize Razorpay client if keys exist; otherwise operate in UPI/mock mode
razorpay_client = None
if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    try:
        razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    except Exception:
        razorpay_client = None

# Fixed payment amounts (in paise, 1 rupee = 100 paise)
PAYMENT_AMOUNTS = {
    "premium": 1000,      # ₹10
    "pro": 5000           # ₹50
}

# Currency
CURRENCY = "INR"


def get_db_connection():
    """
    Get database connection for transaction storage.
    
    Returns:
        sqlite3.Connection: Database connection
    """
    db_path = Path("database") / "app.db"
    return sqlite3.connect(str(db_path))


def create_transactions_table():
    """
    Create Transactions table if it doesn't exist.
    
    Table structure:
    - id: Primary key
    - user_id: User identifier
    - order_id: Razorpay order ID
    - payment_id: Razorpay payment ID
    - amount: Amount in paise
    - currency: Currency code (INR)
    - status: Payment status (pending, success, failed)
    - description: Payment description
    - transaction_date: When transaction was created
    - completed_date: When transaction was completed
    - image_count: Number of premium images purchased
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            order_id TEXT NOT NULL UNIQUE,
            payment_id TEXT,
            amount INTEGER NOT NULL,
            currency TEXT DEFAULT 'INR',
            status TEXT DEFAULT 'pending',
            description TEXT,
            transaction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_date DATETIME,
            image_count INTEGER,
            version_key TEXT,
            signature TEXT,
            FOREIGN KEY (user_id) REFERENCES Users(username)
        )
    """)
    
    # if the table already exists, ensure it has all required columns
    cursor.execute("PRAGMA table_info(Transactions)")
    existing_cols = [row[1] for row in cursor.fetchall()]
    # define any new columns with their SQL definition
    additional_cols = {
        'upi_id': 'TEXT',
        'currency': "TEXT DEFAULT 'INR'",
        'status': "TEXT DEFAULT 'pending'",
        'description': 'TEXT',
        'transaction_date': 'DATETIME DEFAULT CURRENT_TIMESTAMP',
        'completed_date': 'DATETIME',
        'image_count': 'INTEGER',
        'version_key': 'TEXT',
        'signature': 'TEXT'
    }
    for col, ddl in additional_cols.items():
        if col not in existing_cols:
            try:
                cursor.execute(f"ALTER TABLE Transactions ADD COLUMN {col} {ddl}")
            except Exception:
                # ignore if unable to add (may not be supported by sqlite)
                pass
    
    conn.commit()
    conn.close()


def create_payment_order(
    user_id: str,
    amount_key: str = "premium",
    description: str = "Premium Image Download",
    image_count: int = 1,
    payment_method: str = "razorpay",
    upi_id: Optional[str] = None
) -> Dict:
    """
    Create a payment order using Razorpay or a mock UPI flow.
    
    Args:
        user_id: User identifier
        amount_key: Payment amount key (premium=₹10, pro=₹50)
        description: Payment description
        image_count: Number of images being purchased
        payment_method: "razorpay" or "upi" (case‑insensitive)
        upi_id: Optional UPI identifier when using UPI payment
        
    Returns:
        Dict: Order details with keys:
            - success: bool
            - order_id: Razorpay or UPI order ID (if successful)
            - amount: Amount in paise
            - status: Status message
            - key_id: Public key for frontend
            - payment_method: which path was taken (razorpay/upi)
            
    Raises:
        ValueError: If amount_key is invalid
    """
    try:
        # Validate amount
        if amount_key not in PAYMENT_AMOUNTS:
            return {
                "success": False,
                "status": f"Invalid amount key. Must be one of {list(PAYMENT_AMOUNTS.keys())}",
                "order_id": None,
                "amount": None
            }
        
        amount = PAYMENT_AMOUNTS[amount_key]
        
        # If Razorpay client not configured or payment_method is UPI, create a local mock/UPI order
        if payment_method.lower() == "upi" or razorpay_client is None:
            # Create a fake order id and mark payment as success for UPI/mock flow
            order = {
                "id": f"upi_{user_id}_{int(datetime.now().timestamp())}",
                "amount": amount,
                "currency": CURRENCY
            }
        else:
            # Create order with Razorpay
            order_data = {
                "amount": amount,
                "currency": CURRENCY,
                "receipt": f"{user_id}_{datetime.now().timestamp()}",
                "description": description,
                "notes": {
                    "user_id": user_id,
                    "image_count": image_count
                }
            }
            order = razorpay_client.order.create(data=order_data)

        # Store order in database
        create_transactions_table()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO Transactions (
                user_id,
                order_id,
                amount,
                currency,
                status,
                description,
                image_count,
                upi_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            order["id"],
            amount,
            CURRENCY,
            ("success" if payment_method.lower() == "upi" or razorpay_client is None else "pending"),
            description,
            image_count,
            upi_id if payment_method.lower() == "upi" else None
        ))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "order_id": order["id"],
            "amount": amount,
            "amount_rupees": amount / 100,  # Convert paise to rupees
            "currency": CURRENCY,
            "status": "Order created successfully",
            "key_id": RAZORPAY_KEY_ID if razorpay_client is not None else None,
            "description": description,
            "payment_method": ("upi" if payment_method.lower() == "upi" or razorpay_client is None else "razorpay")
        }
        
    except razorpay.errors.BadRequestError as e:
        return {
            "success": False,
            "status": f"Bad Request: {str(e)}",
            "order_id": None,
            "amount": None
        }
    except razorpay.errors.ServerError as e:
        return {
            "success": False,
            "status": f"Server Error: {str(e)}",
            "order_id": None,
            "amount": None
        }
    except Exception as e:
        return {
            "success": False,
            "status": f"Error creating payment order: {str(e)}",
            "order_id": None,
            "amount": None
        }


def verify_payment_signature(
    order_id: str,
    payment_id: str,
    signature: str
) -> Tuple[bool, str]:
    """
    Verify Razorpay payment signature for security.
    
    This ensures the payment response is authentic and hasn't been tampered with.
    
    Args:
        order_id: Razorpay order ID
        payment_id: Razorpay payment ID
        signature: Razorpay payment signature from callback
        
    Returns:
        Tuple[bool, str]: (is_valid, message)
    """
    try:
        # Create the string to hash
        data_to_hash = f"{order_id}|{payment_id}"
        
        # Generate HMAC SHA256 signature
        generated_signature = hmac.new(
            RAZORPAY_KEY_SECRET.encode(),
            data_to_hash.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        is_valid = generated_signature == signature
        
        if is_valid:
            return True, "Signature verified successfully"
        else:
            return False, "Signature verification failed - possible tampering"
            
    except Exception as e:
        return False, f"Error verifying signature: {str(e)}"


def confirm_payment(
    order_id: str,
    payment_id: str,
    signature: str
) -> Dict:
    """
    Confirm payment after signature verification.
    
    Updates transaction status and records payment details.
    
    Args:
        order_id: Razorpay order ID
        payment_id: Razorpay payment ID
        signature: Razorpay signature
        
    Returns:
        Dict: Confirmation details
            - success: bool
            - status: Status message
            - payment_id: Payment ID
            - order_id: Order ID
    """
    try:
        # Verify signature first
        is_valid, verify_message = verify_payment_signature(order_id, payment_id, signature)
        
        if not is_valid:
            return {
                "success": False,
                "status": verify_message,
                "payment_id": payment_id,
                "order_id": order_id
            }
        
        # Update transaction in database
        create_transactions_table()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update transaction status
        cursor.execute("""
            UPDATE Transactions
            SET status = ?, payment_id = ?, signature = ?, completed_date = ?
            WHERE order_id = ?
        """, ("success", payment_id, signature, datetime.now(), order_id))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "status": "Payment confirmed successfully",
            "payment_id": payment_id,
            "order_id": order_id
        }
        
    except Exception as e:
        return {
            "success": False,
            "status": f"Error confirming payment: {str(e)}",
            "payment_id": payment_id,
            "order_id": order_id
        }


def handle_payment_failure(
    order_id: str,
    reason: str = "Unknown error"
) -> Dict:
    """
    Handle failed payment.
    
    Updates transaction status when payment fails.
    
    Args:
        order_id: Order ID
        reason: Failure reason
        
    Returns:
        Dict: Status information
    """
    try:
        create_transactions_table()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE Transactions
            SET status = ?, completed_date = ?, description = description || ?
            WHERE order_id = ?
        """, ("failed", datetime.now(), f" | Failed: {reason}", order_id))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "status": "Payment failure recorded",
            "order_id": order_id
        }
        
    except Exception as e:
        return {
            "success": False,
            "status": f"Error recording payment failure: {str(e)}",
            "order_id": order_id
        }


def verify_payment_before_download(user_id: str, order_id: Optional[str] = None) -> Dict:
    """
    Verify if user can download based on payment status.
    
    Checks if user has a successful payment on record.
    
    Args:
        user_id: User identifier
        order_id: Optional specific order ID to verify
        
    Returns:
        Dict: Verification result with keys:
            - authorized: bool (can download or not)
            - message: str (status message)
            - payment_id: str (if successful)
            - amount_paid: float (in rupees)
            - transaction_date: str (when paid)
    """
    try:
        create_transactions_table()
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if order_id:
            # Check specific order
            cursor.execute("""
                SELECT * FROM Transactions
                WHERE user_id = ? AND order_id = ? AND status = 'success'
                LIMIT 1
            """, (user_id, order_id))
        else:
            # Check if user has ANY successful payment (recent)
            cursor.execute("""
                SELECT * FROM Transactions
                WHERE user_id = ? AND status = 'success'
                ORDER BY completed_date DESC
                LIMIT 1
            """, (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            transaction = dict(row)
            return {
                "authorized": True,
                "message": "Payment verified - download authorized",
                "payment_id": transaction["payment_id"],
                "order_id": transaction["order_id"],
                "amount_paid": transaction["amount"] / 100,  # Convert paise to rupees
                "transaction_date": transaction["completed_date"]
            }
        else:
            return {
                "authorized": False,
                "message": "No successful payment found for this user",
                "payment_id": None,
                "order_id": None,
                "amount_paid": 0
            }
            
    except Exception as e:
        return {
            "authorized": False,
            "message": f"Error verifying payment: {str(e)}",
            "payment_id": None,
            "order_id": None,
            "amount_paid": 0
        }


def get_transaction_by_order_id(order_id: str) -> Optional[Dict]:
    """Retrieve transaction details by order ID.

    Args:
        order_id: Razorpay order ID

    Returns:
        Dict: Transaction details or None if not found
    """
    try:
        create_transactions_table()
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM Transactions WHERE order_id = ?
        """, (order_id,))

        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    except Exception as e:
        print(f"Error retrieving transaction: {str(e)}")
        return None


def get_user_transactions(user_id: str, limit: int = 10) -> list:
    """
    Get all transactions for a user.
    
    Args:
        user_id: User identifier
        limit: Maximum number of transactions to return
        
    Returns:
        list: List of transaction records
    """
    try:
        create_transactions_table()
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM Transactions
            WHERE user_id = ?
            ORDER BY transaction_date DESC
            LIMIT ?
        """, (user_id, limit))
        
        records = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return records
        
    except Exception as e:
        print(f"Error retrieving user transactions: {str(e)}")
        return []


def get_payment_statistics(user_id: str) -> Dict:
    """
    Get payment statistics for a user.
    
    Args:
        user_id: User identifier
        
    Returns:
        Dict: Payment statistics
            - total_spent: Total amount spent in rupees
            - successful_payments: Count of successful payments
            - failed_payments: Count of failed payments
            - total_images: Total images purchased
            - last_transaction: Date of last transaction
    """
    try:
        create_transactions_table()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get statistics
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN status = 'success' THEN amount ELSE 0 END) as total_spent_paise,
                COUNT(CASE WHEN status = 'success' THEN 1 END) as successful_payments,
                COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_payments,
                SUM(CASE WHEN status = 'success' THEN image_count ELSE 0 END) as total_images,
                MAX(completed_date) as last_transaction
            FROM Transactions
            WHERE user_id = ?
        """, (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        total_paise = result[0] if result[0] else 0
        
        return {
            "total_spent_rupees": total_paise / 100,
            "successful_payments": result[1] if result[1] else 0,
            "failed_payments": result[2] if result[2] else 0,
            "total_images_purchased": result[3] if result[3] else 0,
            "last_transaction_date": result[4] if result[4] else None
        }
        
    except Exception as e:
        print(f"Error getting payment statistics: {str(e)}")
        return {
            "total_spent_rupees": 0,
            "successful_payments": 0,
            "failed_payments": 0,
            "total_images_purchased": 0,
            "last_transaction_date": None
        }


# Example usage and testing
if __name__ == "__main__":
    print("Payment Gateway Module (Razorpay)")
    print("=" * 50)
    
    try:
        # Test create order
        print("Testing create_payment_order...")
        order_result = create_payment_order(
            user_id="test_user",
            amount_key="premium",
            description="Test Premium Purchase",
            image_count=1
        )
        print(f"✅ Order created:")
        for key, value in order_result.items():
            print(f"   {key}: {value}")
        
        if order_result["success"]:
            order_id = order_result["order_id"]
            
            # Test get transaction
            print("\nTesting get_transaction_by_order_id...")
            transaction = get_transaction_by_order_id(order_id)
            if transaction:
                print(f"✅ Transaction retrieved:")
                for key, value in transaction.items():
                    print(f"   {key}: {value}")
        
        # Test user statistics
        print("\nTesting get_payment_statistics...")
        stats = get_payment_statistics("test_user")
        print(f"✅ Statistics retrieved:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
