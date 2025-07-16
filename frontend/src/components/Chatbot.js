import React, { useState } from 'react';

const Chatbot = ({ context }) => {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(false);

  const handleAsk = async () => {
    if (!question.trim()) return;

    setLoading(true);
    setAnswer('');

    try {
      const res = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question,
          context, // full document text or summary
          
        }),
      });

      const data = await res.json();
      setAnswer(data.answer || 'No response from model.');
    } catch (err) {
      console.error(err);
      setAnswer('Error reaching the server.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-container">
      <h2>💬 Ask a Question About the Document</h2>
      <textarea
        rows={3}
        placeholder="Type your question..."
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        style={{ width: '100%', marginBottom: '10px' }}
      />
      <button onClick={handleAsk} disabled={loading}>
        {loading ? 'Asking...' : 'Ask'}
      </button>

      {answer && (
        <div style={{ marginTop: '20px' }}>
          <strong>Answer:</strong>
          <p>{answer}</p>
        </div>
      )}
    </div>
  );
};

export default Chatbot;
