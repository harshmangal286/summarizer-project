import React, { useState, useEffect } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Summarizer from "./components/Summarizer";
import "./style.css";
import "bootstrap/dist/css/bootstrap.min.css";

function App() {
  const [chats, setChats] = useState(() => {
    const storedChats = localStorage.getItem("chatHistory");
    return storedChats ? JSON.parse(storedChats) : [];
  });

  const [currentChat, setCurrentChat] = useState(null);
  const [resetChat, setResetChat] = useState(false);

  useEffect(() => {
    localStorage.setItem("chatHistory", JSON.stringify(chats));
  }, [chats]);

  // 🆕 New Chat
  const handleNewChat = () => {
    // Save current chat if it contains data
    if (currentChat?.file || (currentChat?.summary?.length > 0)) {
      setChats((prevChats) => [...prevChats, currentChat]);
    }

    // Reset chat
    const newChat = { id: Date.now(), file: null, summary: "" };
    setCurrentChat(newChat);
    setResetChat((prev) => !prev);
  };

  // 📝 Add to chat history when summary is generated
  const addToHistory = (file, summary) => {
    const updatedChat = { id: Date.now(), file, summary };
    setCurrentChat(updatedChat);
    setChats((prevChats) => [...prevChats, updatedChat]);
  };

  return (
    <Router>
      <div className="app-container">
        <Sidebar
          chats={chats}
          onNewChat={handleNewChat}
          setCurrentChat={setCurrentChat}
        />
        <div className="content">
          <Routes>
            <Route
              path="/"
              element={
                <Summarizer
                  currentChat={currentChat}
                  addToHistory={addToHistory}
                  resetChat={resetChat}
                />
              }
            />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
