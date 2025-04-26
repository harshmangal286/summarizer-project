import React, { useState, useEffect } from "react";
import AttachFileIcon from "@mui/icons-material/AttachFile";
import "bootstrap/dist/css/bootstrap.min.css";
import axios from "axios";
import "../style.css";
import ReactMarkdown from "react-markdown";
import { Document, Packer, Paragraph, TextRun } from "docx";
import { saveAs } from "file-saver";

const Summarizer = ({ addToHistory, resetChat, currentChat }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileUrl, setFileUrl] = useState(null);
  const [summary, setSummary] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showSummaryMsg, setShowSummaryMsg] = useState(false);
  const [selectedModel, setSelectedModel] = useState("gemini");

  useEffect(() => {
    return () => {
      if (fileUrl) URL.revokeObjectURL(fileUrl);
    };
  }, [fileUrl]);

  useEffect(() => {
    if (currentChat?.file) {
      setSelectedFile(currentChat.file);
      setSummary(formatSummary(currentChat.summary || ""));
      setShowSummaryMsg(true);
      setError("");
      setFileUrl(URL.createObjectURL(currentChat.file));
    } else {
      resetFields();
    }
  }, [currentChat]);

  useEffect(() => {
    if (resetChat) resetFields();
  }, [resetChat]);

  const resetFields = () => {
    setSelectedFile(null);
    setFileUrl(null);
    setSummary([]);
    setError("");
    setShowSummaryMsg(false);
  };

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (!["application/pdf", "text/plain", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"].includes(file.type)) {
      setError("Only PDF, text, and DOCX files are supported.");
      return;
    }

    setSelectedFile(file);
    setError("");
    setSummary([]);
    setShowSummaryMsg(false);
    setFileUrl(URL.createObjectURL(file));
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

  // MARKDOWN TO DOCX PARSER
  const parseMarkdownToDocxParagraphs = (lines) => {
    return lines.map((line) => {
      if (line.startsWith("###")) {
        return new Paragraph({
          children: [new TextRun({ text: line.replace(/^###/, "").trim(), bold: true, size: 28 })],
        });
      } else if (line.startsWith("##")) {
        return new Paragraph({
          children: [new TextRun({ text: line.replace(/^##/, "").trim(), bold: true, size: 32 })],
        });
      } else if (line.startsWith("#")) {
        return new Paragraph({
          children: [new TextRun({ text: line.replace(/^#/, "").trim(), bold: true, size: 36 })],
        });
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
      sections: [
        {
          children: parseMarkdownToDocxParagraphs(summary),
        },
      ],
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

        <select className="form-select mx-3" value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)}>
          <option value="gemini">Google Gemini</option>
          {/* <option value="bart">BART (facebook/bart-large-cnn)</option>
          <option value="t5-large">T5 Large (google/flan-t5-large)</option>
          <option value="t5-base">T5 Base (google/flan-t5-base)</option>
          <option value="t5-small">T5 Small (google/flan-t5-small)</option> */}
        </select>

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
          <h4>File Preview</h4>

          {selectedFile?.type === "application/pdf" ? (
            <iframe
              src={fileUrl}
              width="100%"
              height="600px"
              className="pdf-frame"
              title="PDF Preview"
            ></iframe>
          ) : selectedFile?.type === "text/plain" ? (
            <iframe
              src={fileUrl}
              width="100%"
              height="600px"
              className="pdf-frame"
              title="PDF Preview"
            ></iframe>

          ) : selectedFile?.name.endsWith(".docx") ? (
            <iframe
              src={fileUrl}
              width="100%"
              height="600px"
              className="pdf-frame"
              title="PDF Preview"
            ></iframe>
          ) : (
            <div className="alert alert-danger">Unsupported file type for preview.</div>
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
        </div>
      )}
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
