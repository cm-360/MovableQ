import { getCookie, setCookie } from "{{ url_for('serve_js', filename='utils.js') }}";

(() => {

    let jobKey;


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
                card.classList.add("border-primary");
            } else {
                card.classList.add("border-secondary-subtle");
                card.classList.remove("border-primary");
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
        console.log(formData);
        // TODO select method
    }

    methodForm.addEventListener("submit", event => submitMethodSelection(event));


    // ########## Step 2: Friend Code Mining Info ##########

    // Friend code job submission form
    const fcJobForm = document.getElementById("fcJobForm");


    // ########## Step 2: Mii Mining Info ##########

    // Mii job submission form
    const miiJobForm = document.getElementById("miiJobForm");
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


    // ########## Step 3: LFCS from Mii QR Code  ##########


    // ########## Step 4: msed Mining ##########


    // ########## Step 5: Done  ##########


    // ########## Form Management  ##########

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


    // ########## Step Management  ##########

    // Step 1: Choose Method
    const methodCardCollapse = new bootstrap.Collapse(document.getElementById("methodCardCollapse"), { toggle: false });
    // Step 2: Console Info
    const fcInfoCardCollapse = new bootstrap.Collapse(document.getElementById("fcInfoCardCollapse"), { toggle: false });
    const miiInfoCardCollapse = new bootstrap.Collapse(document.getElementById("miiInfoCardCollapse"), { toggle: false });
    // Step 3: LFCS
    const fcLfcsCardCollapse = new bootstrap.Collapse(document.getElementById("fcLfcsCardCollapse"), { toggle: false });
    const miiLfcsCardCollapse = new bootstrap.Collapse(document.getElementById("miiLfcsCardCollapse"), { toggle: false });
    // Step 4: msed
    const msedCardCollapse = new bootstrap.Collapse(document.getElementById("msedCardCollapse"), { toggle: false });
    // Step 5: Done
    const doneCardCollapse = new bootstrap.Collapse(document.getElementById("doneCardCollapse"), { toggle: false });

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
    
    loadJobKey();


})();