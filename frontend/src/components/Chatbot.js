import React, { useRef, useState } from "react";
import axios from "axios";

const Chatbot = ({ onFirstChat }) => {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  // const [pendingFile, setPendingFile] = useState(null);
  const [firstMessageSent, setFirstMessageSent] = useState(false);
  // const fileInputRef = useRef(null);


  const handleSend = async () => {
    // if (!input.trim() && !pendingFile) return;

    // Add user message
    const newMessage = {
      sender: "user",
      text: input.trim(),
      // file: pendingFile || null,
    };
    setMessages((prev) => [...prev, newMessage]);
    setInput("");

    if (!firstMessageSent) {
      setFirstMessageSent(true);
      onFirstChat?.();
    }

    try {
      const formData = new FormData();
      formData.append("question", newMessage.text || "");
      // if (pendingFile) {
      //   formData.append("file", pendingFile, pendingFile.name);
      // }

      const res = await axios.post("http://localhost:8000/chat", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      // Add bot response to messages
      const botMessage = {
        sender: "bot",
        text:
          (res?.data && (res.data.answer || (res.data.choices?.[0]?.message?.content))) ||
          (res?.data?.error ? `Error: ${res.data.error}` : "Oops! Something went wrong."),
      };
      setMessages((prev) => [...prev, botMessage]);

      // Reset file selection so user can upload again
      // setPendingFile(null);
      // if (fileInputRef.current) {
      //   fileInputRef.current.value = "";
      // }
    } catch (error) {
      console.error("Error:", error);
    }
  };

  // const handleFileChange = (e) => {
  //   if (e.target.files && e.target.files[0]) {
  //     setPendingFile(e.target.files[0]);
  //   }
  // };

  return (
    <div className="chatbot-container mt-4">
      <h5>Chat with Document</h5>
      <div className="chat-messages border rounded p-3 mb-2" style={{ height: "300px", overflowY: "auto" }}>
        {messages.map((msg, idx) => (
          <div key={idx} className={`chat-message ${msg.sender}`}>
            <strong>{msg.sender === "user" ? "You" : "Bot"}:</strong> {msg.text}
            {/* {msg.file && <div>📎 {msg.file.name}</div>} */}
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
        {/* <input type="file" id="chat-file" ref={fileInputRef} onChange={handleFileChange} /> */}
        <button className="btn btn-primary" onClick={handleSend}>
          Send
        </button>
      </div>
    </div>
  );
};

export default Chatbot;
