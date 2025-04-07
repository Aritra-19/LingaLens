function showUploadField(type) {
  const fileUpload = document.getElementById("file-upload")
  const uploadSection = document.getElementById("upload-section")
  const originalTextBox = document.getElementById("box-c")

  // Hide first to reset animation
  fileUpload.style.opacity = "0"

  // Set a slight delay before showing again
  setTimeout(() => {
    // Set file type based on button clicked
    if (type === "pdf") {
      fileUpload.setAttribute("accept", "application/pdf")
    } else if (type === "image") {
      fileUpload.setAttribute("accept", "image/*")
    }

    // Show upload field with smooth animation
    uploadSection.classList.remove("hidden")
    fileUpload.style.opacity = "1"
  }, 200)

  // Restore original text box if Enter Text was clicked before
  originalTextBox.innerHTML = `
      <h3>Original Text</h3>
      <p id="original-text">Your scanned text will appear here...</p>
  `

  // Make sure translated text box exists and is ready
  const translatedTextBox = document.getElementById("box-d")
  if (translatedTextBox) {
    translatedTextBox.innerHTML = `
      <h3>Translated Text</h3>
      <p id="translated-text">Translation will appear here...</p>
    `
  }
}

function enterText() {
  const fileUpload = document.getElementById("file-upload")
  const uploadSection = document.getElementById("upload-section")
  const originalTextBox = document.getElementById("box-c")

  // Hide upload field smoothly
  fileUpload.style.opacity = "0"
  setTimeout(() => {
    uploadSection.classList.add("hidden")
  }, 300)

  // Replace original text box with a text input field
  originalTextBox.innerHTML = `
      <h3>Original Text</h3>
      <textarea id="text-input" class="text-input" placeholder="Enter text here..."></textarea>
  `
    
  // Make sure translated text box exists and is ready
  const translatedTextBox = document.getElementById("box-d")
  if (translatedTextBox) {
    // Preserve existing translated text if any, otherwise reset
    const existingTranslatedText = document.getElementById("translated-text")?.textContent || "Translation will appear here..."
    
    translatedTextBox.innerHTML = `
        <h3>Translated Text</h3>
        <p id="translated-text">${existingTranslatedText}</p>
    `
  }
}

async function submitData() {
  const selectedLanguage = document.getElementById("language").value
  const formData = new FormData()
  formData.append("language", selectedLanguage)

  // Get elements - might be null depending on which input method is active
  const originalTextElement = document.getElementById("original-text")
  const translatedTextElement = document.getElementById("translated-text")
  const fileUpload = document.getElementById("file-upload")
  const textInput = document.getElementById("text-input")

  try {
    // Check if a file is uploaded
    if (fileUpload && fileUpload.files.length > 0) {
      const file = fileUpload.files[0]
      formData.append("image", file)

      // Show loading state only if element exists
      if (originalTextElement) {
        originalTextElement.textContent = "Processing..."
      }
      if (translatedTextElement) {
        translatedTextElement.textContent = "Translating..."
      }
    }
    // Check if text is provided
    else if (textInput && textInput.value.trim() !== "") {
      formData.append("text", textInput.value.trim())

      // Show loading state only if element exists
      if (translatedTextElement) {
        translatedTextElement.textContent = "Translating..."
      }
    }
    // If neither is provided
    else {
      alert("Please provide either text or a file.")
      return
    }

    const response = await fetch("/process_image", {
      method: "POST",
      body: formData,
    })

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`)
    }

    const data = await response.json()

    if (data.error) {
      alert("Error: " + data.error)
      if (translatedTextElement) {
        translatedTextElement.textContent = "Translation failed."
      }
      return
    }

    // Display results - safely check for existence first
    if (originalTextElement) {
      originalTextElement.textContent = data.original_text || "No original text found."
    } else if (textInput) {
      // If we're in text input mode, the original text is already visible in the textarea
      console.log("Original text already visible in textarea")
    }
    
    if (translatedTextElement) {
      translatedTextElement.textContent = data.translated_text || "No translated text available."
    } else {
      // Create the translated text element if it doesn't exist
      const boxD = document.getElementById("box-d")
      if (boxD) {
        boxD.innerHTML = `
          <h3>Translated Text</h3>
          <p id="translated-text">${data.translated_text || "No translated text available."}</p>
        `
      }
    }
  } catch (error) {
    console.error("Error during translation:", error)
    alert("Error: " + error.message)
    if (translatedTextElement) {
      translatedTextElement.textContent = "Translation failed."
    }
  }
}

function logout() {
  // Show the popup
  const popup = document.getElementById("logout-popup")
  popup.style.display = "block"

  // Clear any user data from localStorage
  localStorage.removeItem("user")

  // Send logout request to server
  fetch("/logout", {
    method: "POST",
  })
    .then((response) => response.json())
    .then((data) => {
      console.log("Logout successful:", data)
      // Continue with redirection
    })
    .catch((error) => {
      console.error("Error during logout:", error)
      // Continue with redirection even if server request fails
    })
    .finally(() => {
      // Hide popup after 2 seconds and redirect
      setTimeout(() => {
        popup.style.display = "none"
        // Redirect to root path instead of "body.html"
        window.location.href = "/"
      }, 2000)
    })
}