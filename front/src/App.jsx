import React, { useState, useEffect } from "react";
import Files from "react-files";
import axios from "axios";
import "./App.css";

// --- ICONS ---
const IconPlus = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
);
const IconSend = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
);
const IconSettings = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
);
const IconFile = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path><polyline points="13 2 13 9 20 9"></polyline></svg>
);
const IconX = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
);
const IconDownload = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
);

const api = "http://127.0.0.1:5000";

const App = () => {
  const [freeFile, setFreeFile] = useState([]);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [prompt, setPrompt] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchServerFiles();
  }, []);

  const fetchServerFiles = async () => {
    try {
      const response = await axios.get(`${api}/files`);
      if (response.data && Array.isArray(response.data)) {
        setFreeFile(response.data);
      }
    } catch (error) {
      console.error("Error fetching files:", error);
    }
  };

  const handleDeleteServerFile = async (fileName) => {
    try {
      setFreeFile((prev) => prev.filter((f) => f.name !== fileName));
      await axios.delete(`${api}/files/${fileName}`);
    } catch (error) {
      console.error("Error deleting file:", error);
      fetchServerFiles();
    }
  };

  const handleDownload = async (fileName) => {
    try {
      const response = await axios.get(`${api}/files/${fileName}`, {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", fileName);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Error downloading file:", error);
      alert("Failed to download file.");
    }
  };

  const onFilesChange = (files) => {
    setSelectedFiles((prev) => [...prev, ...files]);
  };

  const removeFile = (fileToRemove) => {
    setSelectedFiles(selectedFiles.filter((f) => f !== fileToRemove));
  };

  const handleSubmit = async () => {
    if (!prompt && selectedFiles.length === 0) return;

    const userMsg = {
      role: "user",
      text: prompt,
      files: selectedFiles.map((f) => f.name),
    };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    const formData = new FormData();
    formData.append("prompt", prompt);
    formData.append("api_key", apiKey);
    selectedFiles.forEach((file) => formData.append("files", file));

    setPrompt("");
    setSelectedFiles([]);

    try {

      const result = await axios.post(`${api}`, formData);
      const responseText = result.data.error || result.data.message || "No response text";
      const responseSource = Array.isArray(result.data.sources) ? result.data.sources : [];
      const botMsg = {
        role: "bot",
        text: responseText,
        source: responseSource,
      };
      setMessages((prev) => [...prev, botMsg]);
      fetchServerFiles();
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: "bot", text: "Error: Could not connect to backend." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fullscreen-layout">
      {/* SIDEBAR */}
      <div className="sidebar">
        <div className="sidebar-header">
          <h2>AI Dashboard</h2>
        </div>

        <div className="sidebar-content">
          <div className="section-title">CONFIGURATION</div>
          <div className="api-section">
            <div className="input-group">
              <IconSettings />
              <input
                type="password"
                placeholder="Paste API Key here..."
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
              />
            </div>
          </div>

          <div className="section-title">SERVER FILES</div>
          <div className="file-history">
            {freeFile.length === 0 ? (
              <div className="empty-files">
                <p>No files found</p>
              </div>
            ) : (
              freeFile.map((file, index) => (
                <div key={index} className="history-item">
                  <div className="file-info" style={{ display: "flex", alignItems: "center", gap: "8px", overflow: "hidden", flex: 1 }}>
                    <IconFile />
                    <span style={{ textOverflow: "ellipsis", whiteSpace: "nowrap", overflow: "hidden" }}>
                      {file.name}
                    </span>
                  </div>
                  <div style={{ display: "flex", gap: "2px" }}>
                    <button
                      className="icon-btn-small"
                      onClick={() => handleDownload(file.name)}
                      title="Download PDF"
                    >
                      <IconDownload />
                    </button>
                    <button
                      className="icon-btn-small"
                      onClick={() => handleDeleteServerFile(file.name)}
                      title="Delete file"
                    >
                      <IconX />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="sidebar-footer">
          <p>Status: <span className="status-online">● Online</span></p>
        </div>
      </div>

      {/* MAIN CONTENT */}
      <div className="main-content">
        <div className="chat-container">
          {messages.length === 0 ? (
            <div className="empty-state">
              <h1>Welcome Back</h1>
              <p>Upload files or type a prompt to begin analysis.</p>
            </div>
          ) : (
            messages.map((msg, index) => (
              <div key={index} className={`message ${msg.role}`}>
                <div className="message-bubble">
                  {msg.files && msg.files.length > 0 && (
                    <div className="msg-files">
                      Attached: {msg.files.join(", ")}
                    </div>
                  )}

                  {/* Main Message Text */}
                  <div className="msg-text">
                    {msg.text}
                  </div>

                  {/* Sources Section */}
                  {msg.role === "bot" && msg.source && msg.source.length > 0 && (
                    <div className="msg-sources">
                      <strong>Sources:</strong>
                      {msg.source.map((src, idx) => (
                        <div key={idx} className="source-item">
                          <p>
                            <span className="source-label">Document: </span>
                            {src.document_name}
                          </p>
                          <p>
                            <span className="source-label">Page: </span>
                            {src.page}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
          {loading && <div className="loading-indicator">Thinking...</div>}
        </div>

        {/* INPUT AREA */}
        <div className="input-area">
          {selectedFiles.length > 0 && (
            <div className="file-chips-container">
              {selectedFiles.map((file, i) => (
                <div key={i} className="file-chip">
                  <span>{file.name}</span>
                  <button onClick={() => removeFile(file)}>
                    <IconX />
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="input-bar">
            <Files
              className="files-dropzone"
              onChange={onFilesChange}
              onError={(err) => console.log(err)}
              accepts={["image/*", ".pdf", "audio/*", ".csv"]}
              multiple
              clickable
            >
              <button className="icon-btn" title="Upload File">
                <IconPlus />
              </button>
            </Files>

            <textarea
              placeholder="Send a message..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit();
                }
              }}
            />

            <button
              className="send-btn"
              onClick={handleSubmit}
              disabled={!prompt}
            >
              <IconSend />
            </button>
          </div>
          <div className="disclaimer">
            AI can make mistakes. Verify important info.
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;