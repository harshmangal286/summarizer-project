
const summarizeFile = async (file) => {
  try {
    const formData = new FormData();
    formData.append("file", file);

    console.log("Sending file:", file.name);

    const response = await fetch("http://127.0.0.1:8000/summarize", {
      method: "POST",
      body: formData,
    });

    console.log("Response status:", response.status);

    if (!response.ok) {
      throw new Error(`Server responded with status: ${response.status}`);
    }

    const data = await response.json();
    console.log("Received data:", data);
    return data;
  } catch (error) {
    console.error("Fetch failed:", error);
    return { summary: "Error fetching summary. Please try again." };
  }
};
 export default summarizeFile;