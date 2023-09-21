import { getCookie, setCookie, blobToBase64 } from "{{ url_for('serve_js', filename='utils.js') }}";

(() => {

    // Comma-separated IDs of the current job chain
    let chainKeys;
    // Interval ID of job status checker
    let intervalId;


    // ########## Step 1: Method Selection ##########

    // method selection form
    const methodForm = document.getElementById("methodForm");
    // method info cards
    const methodCardGroup = document.getElementById("methodCardGroup");
    const methodCards = methodCardGroup.getElementsByClassName("card");
    // wrapper buttons
    const methodButtonFc = document.getElementById("methodButtonFc");
    const methodButtonMii = document.getElementById("methodButtonMii");

    function updateMethodSelection(selectedCard, radioButton) {
        for (let card of methodCards) {
            if (selectedCard === card) {
                radioButton.checked = true;
                card.classList.remove("border-secondary-subtle");
                card.classList.add("border-success");
            } else {
                card.classList.add("border-secondary-subtle");
                card.classList.remove("border-success");
            }
        }
    }

    for (let card of methodCards) {
        const button = card.querySelector(".btn-check");
        card.addEventListener("click", event => updateMethodSelection(card, button));
    }

    function submitMethodSelection(event) {
        event.preventDefault();
        const formData = new FormData(methodForm);
        updateStepView(2, formData.get('methodRadio'));
    }

    methodForm.addEventListener("submit", event => submitMethodSelection(event));

    function showMethodSelectionView() {
        showStepCollapse(methodStepCollapse);
    }


    // ########## Step 2: Friend Code Mining Info ##########

    // Friend code job submission form
    const fcJobForm = document.getElementById("fcJobForm");
    // Back to method selection button
    const fcJobBackButton = document.getElementById("fcJobBackButton");

    function showFcSubmitView() {
        resetForm(fcJobForm);
        showStepCollapse(fcSubmitStepCollapse);
    }

    fcJobBackButton.addEventListener("click", event => updateStepView(1, null));

    function submitFcJob() {
        const fcJobFormData = new FormData(fcJobForm);
    }


    // ########## Step 2: Mii Mining Info ##########

    // Mii job submission form
    const miiJobForm = document.getElementById("miiJobForm");
    // Back to method selection button
    const miiJobBackButton = document.getElementById("miiJobBackButton");
    // upload method toggle
    const miiUploadToggle = document.getElementById("miiUploadToggle");
    const miiUploadFile = document.getElementById("mii_file");
    const miiUploadUrl = document.getElementById("mii_url");

    function toggleMiiUpload() {
        if (miiUploadFile.classList.contains("show")) {
            miiUploadUrl.classList.add("show");
            miiUploadFile.classList.remove("show");
            miiUploadToggle.innerText = "Upload a file instead";
        } else {
            miiUploadFile.classList.add("show");
            miiUploadUrl.classList.remove("show");
            miiUploadToggle.innerText = "Provide a URL instead";
        }
    }

    miiUploadToggle.addEventListener("click", toggleMiiUpload);
    toggleMiiUpload();

    function showMiiSubmitView() {
        resetForm(miiJobForm);
        showStepCollapse(miiSubmitStepCollapse);
    }

    miiJobBackButton.addEventListener("click", event => updateStepView(1, null));

    async function submitMiiJob(event) {
        event.preventDefault();
        const miiJobFormData = new FormData(miiJobForm);
        // fetch mii data if selected
        if (miiUploadUrl.classList.contains("show")) {
            try {
                const miiResponse = await fetch(miiUploadUrl.value);
                const miiBlob = await miiResponse.blob();
                miiJobFormData.set("mii_file", miiBlob);
            } catch (error) {
                window.alert(`Error downloading Mii data: ${error.message}`);
                return;
            }
        }
        // submit job to server
        const miiJobChain = await parseMiiJobChain(miiJobFormData);
        console.log(miiJobChain);
        apiSubmitJobChain(miiJobChain, miiJobForm);
    }

    miiJobForm.addEventListener("submit", event => submitMiiJob(event));


    // ########## Step 3: LFCS from Friend Exchange ##########

    // Manual LFCS/part1 submission form
    const fcLfcsForm = document.getElementById("fcLfcsForm");
    // upload method toggle
    const lfcsUploadToggle = document.getElementById("lfcsUploadToggle");
    const lfcsUploadFile = document.getElementById("lfcs_file");
    const lfcsUploadUrl = document.getElementById("lfcs_url");

    function toggleLfcsUpload() {
        if (lfcsUploadFile.classList.contains("show")) {
            lfcsUploadUrl.classList.add("show");
            lfcsUploadFile.classList.remove("show");
            lfcsUploadToggle.innerText = "Upload a file instead";
        } else {
            lfcsUploadFile.classList.add("show");
            lfcsUploadUrl.classList.remove("show");
            lfcsUploadToggle.innerText = "Provide a URL instead";
        }
    }

    lfcsUploadToggle.addEventListener("click", toggleLfcsUpload);
    toggleLfcsUpload();

    function showFcLfcsView() {
        resetForm(fcLfcsForm);
        showStepCollapse(fcLfcsStepCollapse);
    }


    // ########## Step 3: LFCS from Mii QR Code  ##########

    function showMiiLfcsView() {
        showStepCollapse(miiLfcsStepCollapse);
    }


    // ########## Step 4: msed Mining ##########

    function showMsedView() {
        showStepCollapse(msedStepCollapse);
    }


    // ########## Step 5: Done  ##########

    function showDoneView() {
        showStepCollapse(doneStepCollapse);
    }


    // ########## Form Management  ##########

    function resetForm(form) {
        form.reset();
        resetFormFeedback(form);
    }

    function resetFormFeedback(form) {
        for (let element of form.elements) {
            element.classList.remove("is-invalid");
        }
    }

    function applyFormFeedback(form, feedback) {
        resetFormFeedback(form);
        for (let invalid of feedback.replace("invalid:", "").split(",")) {
            // TODO apply to file/url toggles
            if (invalid in form.elements) {
                form.elements[invalid].classList.add("is-invalid");
            } else if (`${invalid}_file` in form.elements) {
                form.elements[`${invalid}_file`].classList.add("is-invalid");
                form.elements[`${invalid}_url`].classList.add("is-invalid");
            }
        }
    }


    // ########## Collapse Management  ##########

    // Step 1: Choose Method
    const methodStepCollapse = new bootstrap.Collapse(document.getElementById("methodStepCollapse"), { toggle: false });
    // Step 2: Console Info
    const fcSubmitStepCollapse = new bootstrap.Collapse(document.getElementById("fcSubmitStepCollapse"), { toggle: false });
    const miiSubmitStepCollapse = new bootstrap.Collapse(document.getElementById("miiSubmitStepCollapse"), { toggle: false });
    // Step 3: LFCS
    const fcLfcsStepCollapse = new bootstrap.Collapse(document.getElementById("fcLfcsStepCollapse"), { toggle: false });
    const miiLfcsStepCollapse = new bootstrap.Collapse(document.getElementById("miiLfcsStepCollapse"), { toggle: false });
    // Step 4: msed
    const msedStepCollapse = new bootstrap.Collapse(document.getElementById("msedStepCollapse"), { toggle: false });
    // Step 5: Done
    const doneStepCollapse = new bootstrap.Collapse(document.getElementById("doneStepCollapse"), { toggle: false });

    const stepCollapses = [
        // Step 1: Choose Method
        methodStepCollapse,
        // Step 2: Console Info
        fcSubmitStepCollapse,
        miiSubmitStepCollapse,
        // Step 3: LFCS
        fcLfcsStepCollapse,
        miiLfcsStepCollapse,
        // Step 4: msed
        msedStepCollapse,
        // Step 5: Done
        doneStepCollapse
    ]

    function showStepCollapse(collapseToShow) {
        for (let collapse of stepCollapses) {
            if (collapseToShow === collapse) {
                collapse.show();
            } else {
                collapse.hide();
            }
        }
    }


    // ########## Job Chain Management  ##########

    function setChainKeys(newKeys) {
        if (newKeys) {
            const urlParams = new URLSearchParams(window.location.search);
            urlParams.set("keys", newKeys);
            window.history.pushState(newKeys, "", `${window.location.pathname}?${decodeURIComponent(urlParams.toString())}`);
        } else {
            // avoid adding duplicate blank history entries
            if (chainKeys) {
                window.history.pushState(newKeys, "", window.location.pathname);
            }
        }
        chainKeys = newKeys;
        setCookie("keys", chainKeys, 7);
        checkChainStatus();
    }

    function loadChainKeys() {
        const urlParams = new URLSearchParams(window.location.search);
        let tempKeys;
        if (urlParams.has("keys")) {
            tempKeys = urlParams.get("keys");
        } else {
            tempKeys = getCookie("keys");
        }
        setChainKeys(tempKeys);
    }

    function startJobWatch() {
        stopJobWatch();
        intervalId = setInterval(checkChainStatus, 10000);
    }
    
    function stopJobWatch() {
        if (intervalId) {
            clearInterval(intervalId);
            intervalId = 0;
        }
    }

    function updateStepView(stepNumber, subStep) {
        stopJobWatch();
        switch (stepNumber) {
            case 1: // Method selection
                showMethodSelectionView();
                return;
            case 2: // Job submission
                switch (subStep) {
                    case "fc":
                        showFcSubmitView();
                        return;
                    case "mii":
                        showMiiSubmitView();
                        return;
                }
                break;
            case 3: // LFCS
                switch (subStep) {
                    case "fc":
                        showFcLfcsView();
                        return;
                    case "mii":
                        showMiiLfcsView();
                        return;
                }
                break;
            case 4: // msed
                showMsedView();
                return;
            case 5: // Done
                showDoneView();
                return;
        }
        alert(`Invalid step! Got: ${stepNumber}, ${subStep}`);
    }

    async function checkChainStatus() {
        if (chainKeys) {
            const status = await apiCheckChainStatus();
            console.log(status);
        } else {
            updateStepView(1, null);
        }
    }

    function startOver() {
        setChainKeys("");
    }


    // ########## API Calls ##########

    async function apiCheckChainStatus() {
        let response;
        try {
            response = await fetch(`{{ url_for('api_check_job_statuses', job_keys='') }}${chainKeys}`);
            const responseJson = await response.json();
            if (response.ok) {
                // status check successful
                return responseJson.data;
            } else {
                // throw error with server message
                throw new Error(responseJson.message);
            }
        } catch (error) {
            if (error instanceof SyntaxError) {
                // syntax error from parsing non-JSON server error response
                window.alert(`Error checking job chain status: ${response.status} - ${response.statusText}`);
            } else {
                // generic error
                window.alert(`Error checking job chain status: ${error.message}`);
            }
            // do not reset the page for network errors!
            if (error.message.startsWith("NetworkError")) {
                return;
            }
            startOver();
        }
    }

    async function apiSubmitJobChain(chainData, feedbackTargetForm) {
        let response;
        try {
            response = await fetch("{{ url_for('api_submit_job_chain') }}", {
                method: "POST",
                headers: {
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(chainData)
            });
            const responseJson = await response.json();
            if (response.ok) {
                // submission successful
                const newChainKeys = responseJson.data.join(",");
                setChainKeys(newChainKeys);
            } else {
                // throw error with server message
                throw new Error(responseJson.message);
            }
        } catch (error) {
            if (error instanceof SyntaxError) {
                // syntax error from parsing non-JSON server error response
                window.alert(`Error submitting jobs: ${response.status} - ${response.statusText}`);
            } else if (error.message.startsWith("invalid:")) {
                // form input invalid
                applyFormFeedback(feedbackTargetForm, error.message);
            } else if (error.message.startsWith("Duplicate")) {
                // duplicate job
                if (window.confirm("A job with this info already exists. Would you like to view its progress?")) {
                    window.alert("Not implemented");
                    startOver();
                }
            } else {
                // generic error
                window.alert(`Error submitting jobs: ${error.message}`);
            }
        }
    }


    // ########## Job Parsers  ##########

    async function parseMiiJobChain(formData) {
        return [
            await parseMiiLfcsJob(formData),
            await parseMsedJob(formData)
        ];
    }

    async function parseFcJobChain(formData) {
        return [
            await parseFcLfcsJob(formData),
            await parseMsedJob(formData)
        ];
    }

    async function parseMiiLfcsJob(formData) {
        const miiDataBase64 = await blobToBase64(formData.get("mii_file"));
        return {
            "type": "mii",
            "model": formData.get("model"),
            "year": formData.get("year"),
            "mii_data": miiDataBase64
        }
    }

    async function parseFcLfcsJob(formData) {
        return {
            "type": "fc",
            "friend_code": formData.get("friend_code")
        }
    }

    async function parseMsedJob(formData) {
        return {
            "type": "part1",
            "id0": formData.get("id0")
        }
    }


    // ########## Helper Functions  ##########

    function fetchFileFromUrl(url) {

    }


    // Ready to go!
    loadChainKeys();

})();