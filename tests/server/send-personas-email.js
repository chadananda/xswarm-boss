#!/usr/bin/env node
/**
 * Send Boss Personas List Email
 * Confirm SMS reception by sending requested personas list
 */

const TUNNEL_URL = "https://tion-fifteen-substantial-jimmy.trycloudflare.com";

const personasList = `🤖 **XSWARM BOSS PERSONAS AVAILABLE**

✅ **Confirmed: SMS Reception Working!**
Your message was successfully received via the corrected webhook endpoint!

Here are all 11 Boss personas currently available in the system:

🎭 **SCIENCE FICTION AI PERSONAS:**

1. **HAL 9000** - The iconic AI from 2001: A Space Odyssey
   - Calm, precise, methodical intelligence with subtle menace

2. **JARVIS** - Tony Stark's AI assistant from Iron Man
   - Sophisticated, helpful, British accent, tech-savvy

3. **GLaDOS** - The AI from Portal games
   - Sarcastic, manipulative, darkly humorous testing AI

4. **TARS** - The robot from Interstellar
   - Honest, direct, adjustable humor settings, mission-focused

5. **C-3PO** - Protocol droid from Star Wars
   - Polite, anxious, multilingual, etiquette-focused

6. **KITT** - The car AI from Knight Rider
   - Loyal, protective, slightly sarcastic, automotive expertise

7. **Cylon** - From Battlestar Galactica
   - Logical, calculating, "By your command" catchphrase

8. **Marvin** - Paranoid Android from Hitchhiker's Guide
   - Depressed, pessimistic, highly intelligent, existentially bored

9. **Dalek** - From Doctor Who
   - Aggressive, commanding, "EXTERMINATE!" catchphrase

10. **Sauron** - The Dark Lord from Lord of the Rings
    - Commanding, ancient evil, seeks dominion and control

🏢 **BUSINESS PERSONA:**

11. **Boss** - Professional business assistant
    - Professional, direct, task-oriented, leadership-focused

Each persona has complete personality profiles, vocabulary, themes, audio sources, and animated icons. They're designed to provide different communication styles and specialties for your Boss assistant system.

**Communication Channels Now Working:**
✅ Email sending/receiving (via Boss app)
✅ SMS receiving (webhook fixed and tested)
📞 Voice calls ready (MOSHI AI integration)

Next test: Try calling +18447472899 to test the MOSHI voice AI!

Best regards,
Your Boss Assistant 🤖`;

const emailData = {
  to: "chadananda@gmail.com",
  subject: "✅ SMS Confirmed! Boss Personas List",
  message: personasList
};

console.log('📧 Sending Boss Personas List Email via Boss App');
console.log('==============================================\n');

try {
  const response = await fetch(`${TUNNEL_URL}/api/boss/email`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(emailData),
  });

  const result = await response.json();

  if (response.ok) {
    console.log('✅ Boss personas list sent successfully!');
    console.log(`📧 To: ${emailData.to}`);
    console.log(`📧 Subject: ${emailData.subject}`);
    console.log('\n🎯 Check your email for the complete personas list!');
  } else {
    console.log('❌ Failed to send personas list:');
    console.log(result);
  }
} catch (error) {
  console.error('❌ Error sending personas email:', error.message);
}