import React, { useState } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Summarizer from "./components/Summarizer";
import "./style.css";
import "bootstrap/dist/css/bootstrap.min.css";

function App() {
  const [chats, setChats] = useState([]);
  const [currentChat, setCurrentChat] = useState(null);

  const handleNewChat = () => {
    if (currentChat) {
      setChats((prevChats) => [...prevChats, currentChat]); // Store previous chat
    }
    setCurrentChat({ id: Date.now(), file: null, summary: "" }); // Create a new chat
  };

  const addToHistory = (file, summary) => {
    setCurrentChat((prevChat) => ({ ...prevChat, file, summary }));
  };

  return (
    <Router>
      <div className="app-container">
        <Sidebar chats={chats} onNewChat={handleNewChat} setCurrentChat={setCurrentChat} />
        <div className="content">
          <Routes>
            <Route path="/" element={<Summarizer currentChat={currentChat} addToHistory={addToHistory} />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
