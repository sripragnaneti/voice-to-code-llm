from gtts import gTTS

# This prompt is designed to be long, rambling, and architecturally complex.
complex_request = """
I need a comprehensive Python-based Inventory Management System. 
It must involve an abstract base class for 'StockItem' with inherited classes for 'Perishables' and 'Electronics'. 
Implement a custom decorator called 'log_transaction' that saves every sale to a local SQLite database. 
The system needs a recursive backtracking algorithm to optimize storage space across three different warehouse locations. 
Also, please include a CLI interface with a sub-command structure and ensure that all docstrings are written in a mix of English, French, and German for my international team.
Make sure the error handling is extensive and uses custom exception classes for insufficient stock and database lock timeouts.
"""

print("Generating the Stress Test audio... please wait.")
tts = gTTS(text=complex_request, lang='en')
tts.save("complex_input.mp3")
print("Done! You can now upload 'complex_input.mp3' to Aura using the Column 2 (Upload Audio Logic) button.")
