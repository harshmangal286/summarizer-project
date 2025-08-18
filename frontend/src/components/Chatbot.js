import React, { useState } from "react";
import axios from "axios";

const Chatbot = ({ onFirstChat }) => {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [pendingFile, setPendingFile] = useState(null);
  const [firstMessageSent, setFirstMessageSent] = useState(false);


  const handleSend = async () => {
    if (!input.trim() && !pendingFile) return;

    // Add user message
    const newMessage = {
      sender: "user",
      text: input.trim(),
      file: pendingFile || null,
    };
    setMessages((prev) => [...prev, newMessage]);
    setInput("");

    if (!firstMessageSent) {
      setFirstMessageSent(true);
      onFirstChat?.();
    }

    try {
      const formData = new FormData();
      formData.append("question", input.trim());
      formData.append("model", "mistralai/mistral-7b-instruct");

      if (pendingFile?.file) {
        formData.append("file", pendingFile.file, pendingFile.file.name);
      }

      console.log("Request payload:", formData);

      const res = await axios.post("http://127.0.0.1:8000/summarize", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      console.log("Response:", res);

      // Add bot response to messages
      const botMessage = {
        sender: "bot",
        text: res.data.choices?.[0]?.message?.content
          ? res.data.choices?.[0]?.message?.content
          : res.data.error
            ? "Error: " + res.data.error
            : "Oops! Something went wrong.",
      };
      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      console.error("Error:", error);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files[0]) {
      setPendingFile({ file: e.target.files[0] });
    }

  };

  return (
    <div className="chatbot-container mt-4">
      <h5>Chat with Document</h5>
      <div className="chat-messages border rounded p-3 mb-2" style={{ height: "300px", overflowY: "auto" }}>
        {messages.map((msg, idx) => (
          <div key={idx} className={`chat-message ${msg.sender}`}>
            <strong>{msg.sender === "user" ? "You" : "Bot"}:</strong> {msg.text}
            {msg.file && <div>📎 {msg.file.name}</div>}
          </div>
        ))}
      </div>

      <div className="chat-input d-flex gap-2">
        <input
          type="text"
          value={input}
          className="form-control"
          placeholder="Ask a question..."
          onChange={(e) => setInput(e.target.value)}
        />
        <input type="file" id="chat-file" onChange={handleFileChange} />
        <button className="btn btn-primary" onClick={handleSend}>
          Send
        </button>
      </div>
    </div>
  );
};

export default Chatbot;
