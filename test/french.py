from gtts import gTTS

text = "Écris un programme Python pour additionner deux nombres."
tts = gTTS(text=text, lang='fr')

tts.save("output.mp3")
