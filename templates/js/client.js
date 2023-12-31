import { getCookie, setCookie, blobToBase64 } from "{{ url_for('serve_js', filename='utils.js') }}";

(() => {

    // Allows URL to forcibly select method
    let forcedMethod = "";
    const forcedMethodPrefix = "{{ url_for('page_force_method', method_name='') }}";
    if (window.location.pathname.startsWith(forcedMethodPrefix)) {
        forcedMethod = window.location.pathname.replace(forcedMethodPrefix, '') + "-lfcs";
    }

    // Comma-separated IDs of the current job chain
    let chainKeys;
    // Interval ID of job status checker
    let intervalId;
    // flag for preventing submission spamming
    let submitting = false;


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
        updateStepView(2, formData.get("methodRadio"));
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

    if (forcedMethod) {
        fcJobBackButton.classList.add("disabled");
    }
    fcJobBackButton.addEventListener("click", event => updateStepView(1));

    async function submitFcJob(event) {
        event.preventDefault();
        if (submitting) {
            return;
        }
        const fcJobFormData = new FormData(fcJobForm);
        // submit job to server
        const fcJobChain = await parseFcJobChain(fcJobFormData);
        console.log(fcJobChain);
        apiSubmitJobChain(fcJobChain, fcJobForm);
    }

    fcJobForm.addEventListener("submit", event => submitFcJob(event));


    // ########## Step 2: Mii Mining Info ##########

    // Mii job submission form
    const miiJobForm = document.getElementById("miiJobForm");
    // Back to method selection button
    const miiJobBackButton = document.getElementById("miiJobBackButton");
    // console year field collapse
    const miiConsoleYearCollapse = document.getElementById("miiConsoleYearCollapse");
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

    if (forcedMethod) {
        miiJobBackButton.classList.add("disabled");
    }
    miiJobBackButton.addEventListener("click", event => updateStepView(1));

    async function submitMiiJob(event) {
        event.preventDefault();
        if (submitting) {
            return;
        }
        const miiJobFormData = new FormData(miiJobForm);
        // process console selection
        let consoleSplit = miiJobFormData.get("model").split(",");
        let consoleType = consoleSplit[0];
        let consoleYear = consoleSplit[1];
        miiJobFormData.set("model", consoleType);
        if (!miiConsoleYearCollapse.classList.contains("show") || !miiJobFormData.get("year")) {
            miiJobFormData.set("year", consoleYear);
        }
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
    // job info
    const botFriendCode = document.getElementById("botFriendCode");
    const fcLfcsStatus = document.getElementById("fcLfcsStatus");
    // cancel button
    const fcLfcsCancelButton = document.getElementById("fcLfcsCancelButton");

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

    function formatFriendCode(friendCode) {
        return friendCode.match(/.{1,4}/g).join("-")
    }

    function showFcLfcsView(jobData) {
        startJobWatch();
        if (jobData.mining_stats.assignee) {
            botFriendCode.innerText = formatFriendCode(jobData.mining_stats.assignee);
        }
        showStepCollapse(fcLfcsStepCollapse);
    }

    fcLfcsCancelButton.addEventListener("click", event => cancelJobs(chainKeys.split(",")));

    async function submitFcLfcs(event) {
        event.preventDefault();
        const fcLfcsFormData = new FormData(fcLfcsForm);
        // fetch part1 data if selected
        if (lfcsUploadUrl.classList.contains("show")) {
            try {
                const lfcsResponse = await fetch(lfcsUploadUrl.value);
                const lfcsBlob = await lfcsResponse.blob();
                fcLfcsFormData.set("lfcs_file", lfcsBlob);
            } catch (error) {
                window.alert(`Error downloading LFCS data: ${error.message}`);
                return;
            }
        }
        // upload LFCS to server
        const fcLfcsResultUpload = await parseFcLfcsUpload(fcLfcsFormData);
        console.log(fcLfcsResultUpload);
        const fcJobKey = chainKeys.split(",")[0];
        await apiCompleteJob(fcJobKey, fcLfcsResultUpload);
        checkChainStatus();
    }

    fcLfcsForm.addEventListener("submit", event => submitFcLfcs(event));


    // ########## Step 3: LFCS from Mii QR Code  ##########

    // job info
    const miiLfcsStatus = document.getElementById("miiLfcsStatus");
    const miiLfcsSysId = document.getElementById("miiLfcsSysId");
    const miiLfcsAssignee = document.getElementById("miiLfcsAssignee");
    // mining stats
    const miiLfcsStatsCollapse = new bootstrap.Collapse(document.getElementById("miiLfcsStatsCollapse"), { toggle: false });
    const miiLfcsStatHash = document.getElementById("miiLfcsStatHash");
    const miiLfcsStatOffset = document.getElementById("miiLfcsStatOffset");
    // cancel button
    const miiLfcsCancelButton = document.getElementById("miiLfcsCancelButton");

    function showMiiLfcsView(jobStatus) {
        startJobWatch();
        miiLfcsSysId.innerText = jobStatus.key;
        miiLfcsAssignee.innerText = jobStatus.mining_stats.assignee;
        showStepCollapse(miiLfcsStepCollapse);
    }

    miiLfcsCancelButton.addEventListener("click", event => cancelJobs(chainKeys.split(",")));


    // ########## Step 4: msed Mining ##########

    // job info
    const msedStatus = document.getElementById("msedStatus");
    const msedId0 = document.getElementById("msedId0");
    const msedLfcs = document.getElementById("msedLfcs");
    // mining stats
    const msedStatsCollapse = new bootstrap.Collapse(document.getElementById("msedStatsCollapse"), { toggle: false });
    const msedStatHash = document.getElementById("msedStatHash");
    const msedStatOffset = document.getElementById("msedStatOffset");
    // cancel button
    const msedCancelButton = document.getElementById("msedCancelButton");

    function showMsedView(jobStatus) {
        startJobWatch();
        msedId0.innerText = jobStatus.key;
        msedLfcs.innerText = jobStatus.mining_stats.lfcs;
        showStepCollapse(msedStepCollapse);
    }

    msedCancelButton.addEventListener("click", event => cancelJob(chainKeys.split(",")[1]));


    // ########## Step 5: Done  ##########

    const movableDownload = document.getElementById("movableDownload");
    const doAnotherButton = document.getElementById("doAnotherButton");

    function showDoneView(id0) {
        movableDownload.href = `{{ url_for('download_movable', id0='') }}${id0}`
        showStepCollapse(doneStepCollapse);
    }

    doAnotherButton.addEventListener("click", event => startOver());


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


    // ########## Step Collapse Management  ##########

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

    // for debugging
    function showAllStepCollapses() {
        for (let collapse of stepCollapses) {
            collapse.show();
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

    function updateStepView(stepNumber, subStep=null, extraInfo=null) {
        stopJobWatch();
        switch (stepNumber) {
            case 1: // Method selection
                showMethodSelectionView();
                return;
            case 2: // Job submission
                switch (subStep) {
                    case "fc-lfcs":
                        showFcSubmitView();
                        return;
                    case "mii-lfcs":
                        showMiiSubmitView();
                        return;
                }
                break;
            case 3: // LFCS
                switch (subStep) {
                    case "fc-lfcs":
                        showFcLfcsView(extraInfo);
                        return;
                    case "mii-lfcs":
                        showMiiLfcsView(extraInfo);
                        return;
                }
                break;
            case 4: // msed
                showMsedView(extraInfo);
                return;
            case 5: // Done
                showDoneView(extraInfo);
                return;
        }
        alert(`Invalid step! Got: ${stepNumber}, ${subStep}`);
    }

    async function checkChainStatus() {
        if (chainKeys) {
            const chainStatus = await apiCheckChainStatus();
            console.log(chainStatus);
            const lfcsJob = chainStatus[0];
            const msedJob = chainStatus[1];
            // check status
            if ("nonexistent" === msedJob.status) {
                // msed job not found
                alert(`Unknown job! Key: ${msedJob.key}`);
                startOver();
            } else if ("done" === msedJob.status) {
                // done view
                updateStepView(5, null, msedJob.key);
            } else if ("nonexistent" === lfcsJob.status) {
                // lfcs job not found
                alert(`Unknown job! Key: ${lfcsJob.key}`);
                startOver();
            } else if ("done" === lfcsJob.status) {
                // msed status view
                updateStepView(4, null, msedJob);
            } else {
                // lfcs status view
                updateStepView(3, lfcsJob.type, lfcsJob);
            }
        } else {
            if (forcedMethod) {
                // form submission view
                updateStepView(2, forcedMethod);
            } else {
                // method selection view
                updateStepView(1);
            }
        }
    }

    function startOver() {
        submitting = false;
        setChainKeys("");
    }

    function cancelJob(jobKey) {
        if (!window.confirm("Are you sure you want to cancel this job?")) {
            return;
        }
        apiCancelJob(jobKey);
        startOver();
    }

    function cancelJobs(jobKeys) {
        if (!window.confirm("Are you sure you want to cancel these jobs?")) {
            return;
        }
        for (let jobKey of jobKeys) {
            apiCancelJob(jobKey);
        }
        startOver();
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
        if (submitting) {
            return;
        }
        submitting = true;
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
                submitting = false;
            }
        } catch (error) {
            submitting = false;
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

    async function apiCancelJob(jobKey) {
        let response;
        try {
            response = await fetch(`{{ url_for('api_cancel_job', key='') }}${jobKey}`);
            const responseJson = await response.json();
            if (!response.ok) {
                throw new Error(responseJson.message);
            }
        } catch (error) {
            if (error instanceof SyntaxError) {
                // syntax error from parsing non-JSON server error response
                window.alert(`Error canceling job: ${response.status} - ${response.statusText}`);
            } else {
                // generic error
                window.alert(`Error canceling job: ${error.message}`);
            }
        }
    }

    async function apiCompleteJob(jobKey, resultData) {
        let response;
        try {
            response = await fetch(`{{ url_for('api_complete_job', key='') }}${jobKey}`, {
                method: "POST",
                headers: {
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(resultData)
            });
            const responseJson = await response.json();
            if (!response.ok) {
                throw new Error(responseJson.message);
            }
        } catch (error) {
            if (error instanceof SyntaxError) {
                // syntax error from parsing non-JSON server error response
                window.alert(`Error completing job: ${response.status} - ${response.statusText}`);
            } else {
                // generic error
                window.alert(`Error completing job: ${error.message}`);
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
            "type": "mii-lfcs",
            "model": formData.get("model"),
            "year": formData.get("year"),
            "mii_data": miiDataBase64
        }
    }

    async function parseFcLfcsJob(formData) {
        return {
            "type": "fc-lfcs",
            "friend_code": formData.get("friend_code")
        }
    }

    async function parseMsedJob(formData) {
        return {
            "type": "msed",
            "id0": formData.get("id0")
        }
    }

    async function parseFcLfcsUpload(formData) {
        const lfcsDataBase64 = await blobToBase64(formData.get("lfcs_file").slice(0, 5));
        return {
            "result": lfcsDataBase64,
            "format": "b64"
        }
    }


    // ########## Helper Functions  ##########

    function fetchFileFromUrl(url) {

    }


    document.addEventListener("DOMContentLoaded", () => {
        loadChainKeys();
        // showAllStepCollapses();
    });

})();
