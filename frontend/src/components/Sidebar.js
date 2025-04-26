import React from "react";
import { useNavigate } from "react-router-dom";
import { SidebarData } from "./SidebarData";
import AddIcon from "@mui/icons-material/Add";
import "../style.css";
import { Button } from "@mui/material";

function Sidebar({ chats, onNewChat, setCurrentChat }) {
  const navigate = useNavigate();

  return (
    <div className="Sidebar">
      <ul className="SidebarList">
        {SidebarData.map((val, key) => (
          <li
            key={key}
            className="row"
            id={window.location.pathname === val.link ? "active" : ""}
            onClick={() => navigate(val.link)}
          >
            <div className="sidebar-icon">{val.icon}</div>
            <div className="sidebar-title">{val.title}</div>
          </li>
        ))}
      </ul>

      {/* New Chat Button */}
      <div className="Newchat">
        <Button variant="contained" color="primary" startIcon={<AddIcon />} fullWidth onClick={onNewChat}>
          New Chat
        </Button>
      </div>

      {/* Display Chat History with File Names */}
      <div className="chat-history">
        <h4>Chat History</h4>
        <ul className = "history-list">
          {chats.length === 0 ? (
            <p className="history-name">No history available.</p>
          ) : (
            chats.map((chat, index) => (
              <li key={index} onClick={() => setCurrentChat(chat)}>
                {chat.file ? chat.file.name : "Untitled Chat"}
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );

  
}




export default Sidebar;
