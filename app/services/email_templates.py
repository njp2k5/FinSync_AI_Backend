def sanction_letter_email(name: str, ref: str):
    return f"""
Hi {name},

Your loan has been approved.
Reference ID: {ref}

Your sanction letter is attached.

Regards,
FinSync AI
"""
