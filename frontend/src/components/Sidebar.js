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
      {/* Static Sidebar Navigation */}
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
        <Button
          variant="contained"
          color="primary"
          startIcon={<AddIcon />}
          fullWidth
          onClick={onNewChat}
        >
          New Chat
        </Button>
      </div>

      {/* Chat History */}
      <div className="chat-history">
        <h4>Chat History</h4>
        <ul className="history-list">
          {chats.length === 0 ? (
          <li className="history-name text-muted">No history available</li>
        ) : (
          chats.map((chat, index) => (
            <li
              key={chat.id || index}
              className="history-name"
              onClick={() => setCurrentChat(chat)}
              style={{ cursor: "pointer" }}
              title={chat.file?.name || `Untitled Chat ${index + 1}`}
            >
              {chat.file?.name || `Untitled Chat ${index + 1}`}
            </li>
          ))
        )}
      </ul>

      <button className="btn btn-sm btn-outline-danger mt-2" onClick={() => {
          localStorage.removeItem("chatHistory");
          window.location.reload(); // or trigger a reset
       }}
      >
  Clear History
</button>


      </div>
    </div>
  );
}

export default Sidebar;