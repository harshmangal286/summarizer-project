import React, { useState, useEffect, useRef } from "react";
import "../style.css";
import { FiPaperclip, FiSmile, FiSend } from "react-icons/fi";

const Chatbot = ({ onFirstChat }) => {

  const [messages, setMessages] = useState([
    { sender: "bot", text: "Hi! Ask me anything about the document." },
  ]);
  const [input, setInput] = useState("");
  const [pendingFile, setPendingFile] = useState(null);
  const [fileExpanded, setFileExpanded] = useState(true);
  const [firstMessageSent, setFirstMessageSent] = useState(false);

  const FileInputRef = useRef(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
  if (!input.trim() && !pendingFile) return;

  const newMessage = {
    sender: "user",
    text: input.trim(),
    file: pendingFile || null,
  };

  setMessages((prev) => [...prev, newMessage]);
  setInput("");
  setPendingFile(null);

if (!firstMessageSent) {
  setFileExpanded(false);        // collapse file
  setFirstMessageSent(true);
  onFirstChat?.();               // notify summarizer to show dropdown
}


  setTimeout(() => {
    setMessages((prev) => [
      ...prev,
      { sender: "bot", text: "Thanks! Let me process that." },
    ]);
  }, 1000);
};


  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const fileURL = URL.createObjectURL(file);
      const isImage = file.type.startsWith("image/");
      setPendingFile({
        type: isImage ? "image" : "file",
        name: file.name,
        url: fileURL,
      });
    }
  };

  const triggerFileInput = () => {
    FileInputRef.current.click();
  };

  return (
    <div className="chatbot-wrapper">
      {/* 🔽 Collapsible File Preview Area (after summarization) */}
      {pendingFile && firstMessageSent && (
        <div className="file-preview-section">
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "6px",
            }}
          >
            <strong>📄 Uploaded File</strong>
            <button
              onClick={() => setFileExpanded((prev) => !prev)}
              style={{
                fontSize: "12px",
                background: "none",
                border: "none",
                color: "#0b5fff",
                cursor: "pointer",
              }}
            >
              {fileExpanded ? "Hide" : "Show"}
            </button>
          </div>

          {fileExpanded && (
            <div
              style={{
                background: "#f9f9f9",
                padding: "10px",
                borderRadius: "10px",
                marginBottom: "10px",
              }}
            >
              {pendingFile.type === "image" ? (
                <img
                  src={pendingFile.url}
                  alt="preview"
                  style={{ maxWidth: "100%", borderRadius: "8px" }}
                />
              ) : (
                <iframe
                  src={pendingFile.url}
                  title="uploaded"
                  style={{
                    width: "100%",
                    height: "300px",
                    border: "none",
                    borderRadius: "8px",
                  }}
                ></iframe>
              )}
            </div>
          )}
        </div>
      )}

      {/* 💬 Chat Messages */}
      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div
            key={i}
            className="chat-message"
            style={{ textAlign: msg.sender === "user" ? "right" : "left" }}
          >
            <span className={`chat-bubble ${msg.sender}`}>
              {/* File Preview First */}
              {msg.file && msg.file.type === "image" && (
                <>
                  <div
                    style={{ fontSize: "12px", marginBottom: "6px" }}
                  >{msg.file.name}</div>
                  <img
                    src={msg.file.url}
                    alt="uploaded"
                    style={{
                      maxWidth: "100%",
                      borderRadius: "10px",
                      marginBottom: "8px",
                    }}
                  />
                </>
              )}
              {msg.file && msg.file.type === "file" && (
                <a
                  href={msg.file.url}
                  download={msg.file.name}
                  style={{
                    display: "inline-block",
                    marginBottom: "8px",
                    color: "#0b5fff",
                    textDecoration: "underline",
                    fontSize: "14px",
                  }}
                >
                  📄 {msg.file.name}
                </a>
              )}
              {/* Text message */}
              {msg.text && <div style={{ whiteSpace: "pre-wrap" }}>{msg.text}</div>}
            </span>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* 🔘 Chat Input Box */}
      <div className="chat-input-container">
        <input
          type="file"
          style={{ display: "none" }}
          ref={FileInputRef}
          onChange={handleFileUpload}
        />

        <button className="chat-icon-button" onClick={triggerFileInput}>
          <FiPaperclip />
        </button>

        {/* File preview in input box (before sending) */}
        {pendingFile && (
          <div
            style={{
              background: "#f1f1f1",
              padding: "8px",
              borderRadius: "12px",
              display: "flex",
              alignItems: "center",
              gap: "10px",
              marginRight: "8px",
              maxWidth: "200px",
            }}
          >
            {pendingFile.type === "image" ? (
              <img
                src={pendingFile.url}
                alt="preview"
                style={{ height: "40px", borderRadius: "6px" }}
              />
            ) : (
              <span style={{ fontSize: "14px" }}>📄 {pendingFile.name}</span>
            )}
            <button
              onClick={() => setPendingFile(null)}
              style={{
                background: "transparent",
                border: "none",
                color: "red",
                fontWeight: "bold",
                cursor: "pointer",
              }}
            >
              ✕
            </button>
          </div>
        )}

        <textarea
          placeholder="Ask me anything..."
          className="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          rows={1}
        />

        <button className="chat-icon-button">
          <FiSmile />
        </button>
        <button className="chat-icon-button" onClick={handleSend}>
          <FiSend />
        </button>
      </div>
    </div>
  );
};

export default Chatbot;