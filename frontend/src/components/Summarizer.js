import React, { useState, useEffect } from "react";
import AttachFileIcon from "@mui/icons-material/AttachFile";
import "bootstrap/dist/css/bootstrap.min.css";
import axios from "axios";
import "../style.css";
import ReactMarkdown from "react-markdown";
import { Document, Packer, Paragraph, TextRun } from "docx";
import { saveAs } from "file-saver";
import Chatbot from "./Chatbot";

const Summarizer = ({ addToHistory, resetChat, currentChat }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileUrl, setFileUrl] = useState(null);
  const [summary, setSummary] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showSummaryMsg, setShowSummaryMsg] = useState(false);
  const [selectedModel, setSelectedModel] = useState("Mistral");
  const [fileExpanded, setFileExpanded] = useState(true);
  const [chatStarted, setChatStarted] = useState(false);

  // Cleanup URL on unmount
  useEffect(() => {
    return () => {
      if (fileUrl) URL.revokeObjectURL(fileUrl);
    };
  }, [fileUrl]);

  // On chat history load
  useEffect(() => {
    if (currentChat?.file) {
      setSelectedFile(currentChat.file);
      setSummary(formatSummary(currentChat.summary || ""));
      setShowSummaryMsg(true);
      setError("");
      setFileUrl(URL.createObjectURL(currentChat.file));
      setFileExpanded(true);
      setChatStarted(false);
    } else {
      resetFields();
    }
  }, [currentChat]);

  // Reset fields on new chat trigger
  useEffect(() => {
    if (resetChat) resetFields();
  }, [resetChat]);

  const resetFields = () => {
    setSelectedFile(null);
    setFileUrl(null);
    setSummary([]);
    setError("");
    setShowSummaryMsg(false);
    setFileExpanded(true);
    setChatStarted(false);
  };

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (
      !["application/pdf", "text/plain", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"].includes(file.type)
    ) {
      setError("Only PDF, text, and DOCX files are supported.");
      return;
    }

    setSelectedFile(file);
    setError("");
    setSummary([]);
    setShowSummaryMsg(false);
    setFileUrl(URL.createObjectURL(file));
    setFileExpanded(true);
  };

  const formatSummary = (text) => {
    return text.split("\n").filter((point) => point.trim() !== "");
  };

  const handleSummarize = async () => {
    if (!selectedFile) {
      alert("Please select a file first!");
      return;
    }

    setLoading(true);
    setError("");
    setSummary([]);
    setShowSummaryMsg(false);

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("model", selectedModel);

    try {
      const response = await axios.post("http://127.0.0.1:8000/summarize", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      const formattedSummary = formatSummary(response.data.summary || "No summary available.");
      setSummary(formattedSummary);
      setShowSummaryMsg(true);
      addToHistory(selectedFile, response.data.summary);
    } catch (err) {
      setError("Failed to summarize. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const parseMarkdownToDocxParagraphs = (lines) => {
    return lines.map((line) => {
      if (line.startsWith("###")) {
        return new Paragraph({ children: [new TextRun({ text: line.replace(/^###/, "").trim(), bold: true, size: 28 })] });
      } else if (line.startsWith("##")) {
        return new Paragraph({ children: [new TextRun({ text: line.replace(/^##/, "").trim(), bold: true, size: 32 })] });
      } else if (line.startsWith("#")) {
        return new Paragraph({ children: [new TextRun({ text: line.replace(/^#/, "").trim(), bold: true, size: 36 })] });
      } else {
        return new Paragraph({
          children: line.split(/\*\*(.*?)\*\*/g).map((part, i) =>
            i % 2 === 1 ? new TextRun({ text: part, bold: true }) : new TextRun(part)
          ),
        });
      }
    });
  };

  const handleDownload = async () => {
    const doc = new Document({
      sections: [{ children: parseMarkdownToDocxParagraphs(summary) }],
    });

    const blob = await Packer.toBlob(doc);
    saveAs(blob, "FormattedSummary.docx");
  };

  return (
    <div className="container text-center">
      <h1 className="text-center">Document Summarizer</h1>
      <p className="lead text-center">Summarize PDF and text documents with ease.</p>

      <div className="button-container">
        {!selectedFile && (
          <label className="btn btn-primary">
            <AttachFileIcon />
            <input type="file" onChange={handleFileChange} accept=".pdf,.txt,.docx" hidden />
            Choose File
          </label>
        )}
        {!showSummaryMsg ? (
          <button className="btn btn-success mx-3" onClick={handleSummarize} disabled={!selectedFile || loading}>
            {loading ? (
              <>
                <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                Processing...
              </>
            ) : (
              "Summarize Document"
            )}
          </button>
        ) : (
          <div className="alert alert-info mx-3">Summary can be viewed below.</div>
        )}
      </div>

      {fileUrl && (
        <div className="file-preview mt-4 mb-4">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h4>
              📄 File Preview {selectedFile?.name && <span style={{ fontWeight: "normal" }}>– "{selectedFile.name}"</span>}
            </h4>
            {chatStarted && (
              <button
                onClick={() => setFileExpanded(!fileExpanded)}
                style={{ background: "none", border: "none", cursor: "pointer", padding: "4px" }}
                title={fileExpanded ? "Collapse preview" : "Expand preview"}
              >
                {fileExpanded ? (
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <path d="M5 8L10 13L15 8" stroke="#0b5fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ) : (
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <path d="M8 5L13 10L8 15" stroke="#0b5fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                )}
              </button>
            )}
          </div>

          {fileExpanded && (
            <div style={{ marginTop: "10px" }}>
              {selectedFile?.type === "application/pdf" || selectedFile?.name.endsWith(".docx") ? (
                <iframe src={fileUrl} width="100%" height="600px" className="pdf-frame" title="PDF Preview"></iframe>
              ) : selectedFile?.type === "text/plain" ? (
                <TextFilePreview file={selectedFile} />
              ) : (
                <div className="alert alert-danger">Unsupported file type for preview.</div>
              )}
            </div>
          )}
        </div>
      )}

      {error && <div className="alert alert-danger mt-3">{error}</div>}

      {summary.length > 0 && (
        <div className="summary-container mt-4">
          <h4>Summary</h4>
          <div className="markdown-summary text-start">
            {summary.map((point, index) => (
              <ReactMarkdown key={index}>{point}</ReactMarkdown>
            ))}
          </div>
          <button className="btn btn-outline-primary mt-3" onClick={handleDownload}>
            Download Summary
          </button>
          <Chatbot
            onFirstChat={() => {
              setChatStarted(true);
              setFileExpanded(false); // Collapse on first chat
            }}
          />
        </div>
      )}

      { /*Chatbot component*/}
      {
        // <Chatbot
        //   onFirstChat={() => {
        //     setChatStarted(true);
        //     setFileExpanded(false); // Collapse on first chat
        //   }}
        // />
      }
    </div>
  );
};

const TextFilePreview = ({ file }) => {
  const [content, setContent] = useState("");

  useEffect(() => {
    const reader = new FileReader();
    reader.onload = (e) => setContent(e.target.result);
    reader.readAsText(file);
  }, [file]);

  return (
    <pre className="text-start p-3 bg-light rounded" style={{ maxHeight: "400px", overflowY: "auto" }}>
      {content}
    </pre>
  );
};

export default Summarizer;