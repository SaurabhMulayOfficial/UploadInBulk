const state = {

    connection: {
        status: "disconnected"
    },

    relation: {
        object: null,
        matchingField: null,
        visibility: null
    },

    files: []
};


// =========================================
// Elements
// =========================================

const connectionStep =
    document.getElementById("connectionStep");

const relationStep =
    document.getElementById("relationStep");

const fileStep =
    document.getElementById("fileStep");


const connectButton =
    document.getElementById("connectButton");

const connectionMessage =
    document.getElementById("connectionMessage");

const connectionDot =
    document.getElementById("connectionDot");

const connectionText =
    document.getElementById("connectionText");


const continueRelationButton =
    document.getElementById(
        "continueRelationButton"
    );

const relationMessage =
    document.getElementById(
        "relationMessage"
    );


const fileInput =
    document.getElementById("fileInput");

const fileSummary =
    document.getElementById("fileSummary");

const fileCount =
    document.getElementById("fileCount");

const fileList =
    document.getElementById("fileList");

const uploadButton =
    document.getElementById("uploadButton");


// =========================================
// Initial State
// =========================================

// Only Step 1 is visible initially.

relationStep.style.display = "none";
fileStep.style.display = "none";


// =========================================
// STEP 1
// Salesforce Connection
// =========================================

connectButton.addEventListener(
    "click",
    handleConnect
);


async function handleConnect() {

    clearConnectionMessage();


    const salesforceUrl =
        document
            .getElementById("salesforceUrl")
            .value
            .trim();


    const clientId =
        document
            .getElementById("clientId")
            .value
            .trim();


    const clientSecret =
        document
            .getElementById("clientSecret")
            .value;


    // -----------------------------------------
    // Validation
    // -----------------------------------------

    if (!salesforceUrl) {

        showConnectionMessage(
            "Please enter your Salesforce URL.",
            "error"
        );

        return;
    }


    if (!clientId) {

        showConnectionMessage(
            "Please enter your Client ID.",
            "error"
        );

        return;
    }


    if (!clientSecret) {

        showConnectionMessage(
            "Please enter your Client Secret.",
            "error"
        );

        return;
    }


    setConnectingState(true);


    // -----------------------------------------
    // Authenticate
    // -----------------------------------------

    try {

        const response = await fetch(
            "/api/auth/login",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({

                    salesforce_url:
                        salesforceUrl,

                    client_id:
                        clientId,

                    client_secret:
                        clientSecret

                })
            }
        );


        const data =
            await response.json();


        if (
            !response.ok ||
            !data.success
        ) {

            throw new Error(
                data.message ||
                "Unable to connect to Salesforce."
            );
        }


        // -----------------------------------------
        // SUCCESS
        // -----------------------------------------

        state.connection.status =
            "connected";


        showConnectionMessage(
            "Successfully connected to Salesforce.",
            "success"
        );


        activateStep1Complete();


    } catch (error) {

        state.connection.status =
            "disconnected";


        showConnectionMessage(
            error.message ||
            "Unable to connect to Salesforce.",
            "error"
        );


        setConnectingState(false);
    }
}


// =========================================
// STEP 1 - Connected
// =========================================

function activateStep1Complete() {

    connectButton.disabled =
        true;


    connectButton.textContent =
        "Connected ✓";


    connectionDot.classList.add(
        "connected"
    );


    connectionText.textContent =
        "Connected";


    connectionStep.classList.add(
        "completed"
    );


    // -----------------------------------------
    // Activate Step 2
    // -----------------------------------------

    relationStep.style.display =
        "block";


    relationStep.classList.add(
        "active"
    );
}


// =========================================
// Connecting State
// =========================================

function setConnectingState(
    isConnecting
) {

    connectButton.disabled =
        isConnecting;


    if (isConnecting) {

        connectButton.textContent =
            "Connecting...";


        showConnectionMessage(
            "Connecting to Salesforce...",
            "loading"
        );

    } else {

        connectButton.textContent =
            "Connect to Salesforce";
    }
}


// =========================================
// STEP 2
// File Relationship
// =========================================

continueRelationButton.addEventListener(
    "click",
    handleRelationContinue
);


function handleRelationContinue() {

    clearRelationMessage();


    const relateObject =
        document
            .getElementById("relateObject")
            .value
            .trim();


    const matchingField =
        document
            .getElementById("matchingField")
            .value
            .trim();


    const visibility =
        document
            .getElementById("fileVisibility")
            .value;


    // -----------------------------------------
    // Validation
    // -----------------------------------------

    // Object provided but matching field missing

    if (
        relateObject &&
        !matchingField
    ) {

        showRelationMessage(
            "Please enter the Matching Field API Name.",
            "error"
        );

        return;
    }


    // Matching field provided but object missing

    if (
        !relateObject &&
        matchingField
    ) {

        showRelationMessage(
            "Please enter the Salesforce Object API Name.",
            "error"
        );

        return;
    }


    // -----------------------------------------
    // Store configuration
    // -----------------------------------------

    state.relation = {

        object:
            relateObject || null,

        matchingField:
            matchingField || null,

        visibility:
            relateObject
                ? visibility
                : null
    };


    console.log(
        "File relationship configuration:",
        state.relation
    );


    // -----------------------------------------
    // Step 2 Complete
    // -----------------------------------------

    relationStep.classList.add(
        "completed"
    );


    // -----------------------------------------
    // Disable Step 2
    // -----------------------------------------

    document
        .getElementById("relateObject")
        .disabled = true;


    document
        .getElementById("matchingField")
        .disabled = true;


    document
        .getElementById("fileVisibility")
        .disabled = true;


    continueRelationButton.disabled =
        true;


    continueRelationButton.textContent =
        "Completed ✓";


    // -----------------------------------------
    // Activate Step 3
    // -----------------------------------------

    fileStep.style.display =
        "block";


    fileStep.classList.add(
        "active"
    );
}


// =========================================
// STEP 3
// File Selection
// =========================================

fileInput.addEventListener(
    "change",
    handleFileSelection
);


function handleFileSelection(event) {

    const selectedFiles =
        Array.from(
            event.target.files
        );


    state.files =
        selectedFiles;


    updateFileDisplay();
}


// =========================================
// Display Selected Files
// =========================================

function updateFileDisplay() {

    fileList.innerHTML = "";


    const count =
        state.files.length;


    fileCount.textContent =
        count;


    if (count === 0) {

        fileSummary.classList.add(
            "hidden"
        );

        uploadButton.disabled =
            true;

        return;
    }


    fileSummary.classList.remove(
        "hidden"
    );


    uploadButton.disabled =
        false;


    // -----------------------------------------
    // Display files
    // -----------------------------------------

    state.files.forEach(
        (file, index) => {

            const row =
                document.createElement(
                    "div"
                );


            row.className =
                "file-row";


            row.innerHTML = `
                <span class="file-index">
                    ${index + 1}
                </span>

                <span class="file-name">
                    ${escapeHtml(file.name)}
                </span>

                <span class="file-size">
                    ${formatFileSize(file.size)}
                </span>
            `;


            fileList.appendChild(row);
        }
    );
}


// =========================================
// File Size
// =========================================

function formatFileSize(bytes) {

    if (bytes === 0) {
        return "0 Bytes";
    }


    const units = [
        "Bytes",
        "KB",
        "MB",
        "GB"
    ];


    const index =
        Math.floor(
            Math.log(bytes) /
            Math.log(1024)
        );


    return (
        parseFloat(
            (
                bytes /
                Math.pow(1024, index)
            ).toFixed(2)
        ) +
        " " +
        units[index]
    );
}


// =========================================
// Escape HTML
// =========================================

function escapeHtml(value) {

    return value
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


// =========================================
// Connection Messages
// =========================================

function showConnectionMessage(
    message,
    type
) {

    connectionMessage.textContent =
        message;


    connectionMessage.className =
        `message ${type}`;
}


function clearConnectionMessage() {

    connectionMessage.textContent =
        "";


    connectionMessage.className =
        "message hidden";
}


// =========================================
// Relation Messages
// =========================================

function showRelationMessage(
    message,
    type
) {

    relationMessage.textContent =
        message;


    relationMessage.className =
        `message ${type}`;
}


function clearRelationMessage() {

    relationMessage.textContent =
        "";


    relationMessage.className =
        "message hidden";
}

const uploadSummary =
    document.getElementById(
        "uploadSummary"
    );

const resultTotal =
    document.getElementById(
        "resultTotal"
    );

const resultUploaded =
    document.getElementById(
        "resultUploaded"
    );

const resultFailed =
    document.getElementById(
        "resultFailed"
    );

const uploadResults =
    document.getElementById(
        "uploadResults"
    );




    uploadButton.addEventListener(
    "click",
    handleUpload
);


async function handleUpload() {

    if (state.files.length === 0) {
        return;
    }

    uploadButton.disabled = true;

    uploadButton.textContent =
        "Uploading...";

    uploadResults.classList.add(
        "hidden"
    );

    uploadSummary.classList.add(
        "hidden"
    );

    try {

        const formData =
            new FormData();

        // Add files
        state.files.forEach(
            file => {

                formData.append(
                    "files",
                    file
                );

            }
        );

        // Add relationship configuration
        if (state.relation.object) {

            formData.append(
                "object_name",
                state.relation.object
            );

            formData.append(
                "field_name",
                state.relation.matchingField
            );

            formData.append(
                "visibility",
                state.relation.visibility
            );
        }

        const response =
            await fetch(
                "/api/files/upload",
                {
                    method: "POST",
                    body: formData
                }
            );

        const data =
            await response.json();

        if (
            !response.ok ||
            !data.success
        ) {
            throw new Error(
                data.message ||
                "File upload failed."
            );
        }

        showUploadResults(data);

    } catch (error) {

        showUploadError(
            error.message ||
            "Unable to upload files."
        );

    } finally {

        uploadButton.disabled =
            false;

        uploadButton.textContent =
            "Upload Files";
    }
}

function showUploadResults(data) {

    resultTotal.textContent =
        data.total || 0;

    resultUploaded.textContent =
        data.uploaded || 0;

    resultFailed.textContent =
        data.failed || 0;

    uploadSummary.classList.remove(
        "hidden"
    );

    uploadResults.innerHTML = "";

    const results =
        data.results || [];

    results.forEach(
        result => {

            const row =
                document.createElement(
                    "div"
                );

            row.className =
                `upload-result-row ${
                    result.status === "uploaded"
                        ? "result-success"
                        : "result-failed"
                }`;

            const status =
                result.status === "uploaded"
                    ? "Uploaded"
                    : "Failed";

            const details =
                result.status === "uploaded"
                    ? `
                        <span class="result-detail">
                            ContentDocument:
                            ${escapeHtml(
                                result.content_document_id || ""
                            )}
                        </span>
                    `
                    : `
                        <span class="result-detail">
                            ${escapeHtml(
                                result.reason || "Unknown error"
                            )}
                        </span>
                    `;

            row.innerHTML = `
                <div class="result-file">
                    ${escapeHtml(
                        result.filename
                    )}
                </div>

                <div class="result-status">
                    <span class="status-badge">
                        ${status}
                    </span>
                </div>

                <div class="result-details">
                    ${details}
                </div>
            `;

            uploadResults.appendChild(
                row
            );
        }
    );

    uploadResults.classList.remove(
        "hidden"
    );
}

function showUploadError(message) {

    uploadSummary.classList.add(
        "hidden"
    );

    uploadResults.innerHTML = `
        <div class="upload-error">
            ${escapeHtml(message)}
        </div>
    `;

    uploadResults.classList.remove(
        "hidden"
    );
}