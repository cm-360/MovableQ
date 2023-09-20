import { getCookie, setCookie } from "{{ url_for('serve_js', filename='utils.js') }}";

(() => {

    // Comma-separated IDs of the current job chain
    let jobKey;
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
            if (selectedCard == card) {
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

    fcJobBackButton.addEventListener("click", event => {
        updateStepView(1, null);
    });

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

    miiJobBackButton.addEventListener("click", event => {
        updateStepView(1, null);
    });

    function submitMiiJob() {
        const miiJobFormData = new FormData(miiJobForm);
    }


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


    // ########## Job Management  ##########

    function setJobKey(newKey) {
        if (newKey) {
            const urlParams = new URLSearchParams(window.location.search);
            urlParams.set("key", newKey);
            window.history.pushState(newKey, "", window.location.pathname + "?" + urlParams.toString());
        } else {
            // avoid adding duplicate blank history entries
            if (jobKey) {
                window.history.pushState(newKey, "", window.location.pathname);
            }
        }
        jobKey = newKey;
        setCookie("key", jobKey, 7);
    }

    function loadJobKey() {
        const urlParams = new URLSearchParams(window.location.search);
        let tmpKey;
        if (urlParams.has("key")) {
            tmpKey = urlParams.get("key");
        } else {
            tmpKey = getCookie("key");
        }
        setJobKey(tmpKey);
    }

    function startJobWatch() {
        stopJobWatch();
        intervalId = setInterval(checkJob, 10000);
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

    function fetchJobStatus() {
        if (jobKey) {

        } else {
            updateStepView(1, null);
        }
    }


    // ########## Helper Functions  ##########

    function fetchFileFromUrl(url) {

    }


    // Ready to go!
    loadJobKey();
    fetchJobStatus();

})();