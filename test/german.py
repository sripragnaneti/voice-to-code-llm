from gtts import gTTS

english_text = "Write a Python program that calculates the factorial of a number."

german_text = "Schreibe ein Python-Programm, das die Fakultät einer Zahl berechnet."

tts = gTTS(text=german_text, lang='de')
tts.save("german_output.mp3")