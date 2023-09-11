import { getCookie, setCookie } from "{{ url_for('serve_js', filename='utils.js') }}";

(() => {

  let id0;
  let intervalId = 0;

  const card1 = new bootstrap.Collapse(document.getElementById("card1"), { toggle: false });
  const card2 = new bootstrap.Collapse(document.getElementById("card2"), { toggle: false });
  const card3 = new bootstrap.Collapse(document.getElementById("card3"), { toggle: false });

  const miiForm = document.getElementById("miiForm");

  const miiUploadToggle = document.getElementById("miiUploadToggle");
  const miiUploadFile = document.getElementById("mii_file");
  const miiUploadUrl = document.getElementById("mii_url");

  const miningId0 = document.getElementById("miningId0");
  const miningStatus = document.getElementById("miningStatus");
  const cancelJobButton = document.getElementById("cancelJobButton");

  const movableDownload = document.getElementById("movableDownload");
  const doAnotherButton = document.getElementById("doAnotherButton");

  const canceledModalEl = document.getElementById("canceledModal");
  const canceledModal = new bootstrap.Modal(canceledModalEl);

  const failedModalEl = document.getElementById("failedModal");
  const failedModal = new bootstrap.Modal(failedModalEl);


  // card UI functions

  function showCard1() {
    cancelJobWatch();
    miiForm.reset();
    // update cards
    card1.show();
    card2.hide();
    card3.hide();
  }

  function showCard2(status) {
    miningId0.innerText = id0;
    switch (status) {
      case "working":
        miningStatus.innerText = "Mining in progress...";
        break;
      case "waiting":
        miningStatus.innerText = "Waiting for an available miner...";
        break;
      default:
        miningStatus.innerText = "Please wait...";
    }
    startJobWatch();
    // update cards
    card1.hide();
    card2.show();
    card3.hide();
  }

  function showCard3() {
    cancelJobWatch();
    movableDownload.href = "{{ url_for('download_movable', id0='') }}" + id0;
    // update cards
    card1.hide();
    card2.hide();
    card3.show();
  }

  function updateCards(status) {
    switch (status) {
      case "done":
        showCard3();
        break;
      case "waiting":
      case "working":
        showCard2(status);
        break;
      case "canceled":
        cancelJobWatch();
        canceledModal.show();
        break;
      case "failed":
        cancelJobWatch();
        failedModal.show();
        break;
      default:
        startOver();
        break;
    }
  }


  // other UI functions

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

  function resetMiiFormFeedback() {
    for (let element of miiForm.elements) {
      element.classList.remove("is-invalid");
    }
  }

  function applyMiiFormFeedback(feedback) {
    resetMiiFormFeedback();
    if (feedback.startsWith("invalid:")) {
      for (let invalid of feedback.replace("invalid:", "").split(",")) {
        if (invalid == "mii") {
          miiForm.elements["mii_file"].classList.add("is-invalid");
          miiForm.elements["mii_url"].classList.add("is-invalid");
        } else {
          miiForm.elements[invalid].classList.add("is-invalid");
        }
      }
    } else {
      window.alert("Error submitting job: " + responseJson.message);
    }
  }


  // actions

  function loadID0() {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has("id0")) {
      setID0(urlParams.get("id0"));
    } else {
      setID0(getCookie("id0"));
    }
  }

  function setID0(new_id0) {
    if (new_id0) {
      const urlParams = new URLSearchParams(window.location.search);
      urlParams.set("id0", new_id0);
      window.history.pushState(new_id0, "", window.location.pathname + "?" + urlParams.toString());
    } else {
      // avoid adding duplicate blank history entries
      if (id0) {
        window.history.pushState(new_id0, "", window.location.pathname);
      }
    }
    id0 = new_id0;
    setCookie("id0", id0, 7);
  }

  function startJobWatch() {
    cancelJobWatch();
    intervalId = setInterval(checkJob, 10000);
  }

  function cancelJobWatch() {
    if (intervalId) {
      clearInterval(intervalId);
      intervalId = 0;
    }
  }

  function startOver() {
    setID0("");
    cancelJobWatch();
    resetMiiFormFeedback();
    showCard1();
  }

  async function submitMiiForm() {
    const formData = new FormData(miiForm);
    if (miiUploadUrl.classList.contains("show")) {
      const miiResponse = await fetch(miiUploadUrl.value);
      if (miiResponse.ok) {
        const miiBlob = await miiResponse.blob();
        formData.set("mii_file", miiBlob);
      } else {
        window.alert("Error submitting job: Failed to download Mii data");
      }
    }
    const response = await fetch("{{ url_for('api_submit_mii_job') }}", {
      method: "POST",
      body: formData
    });
    const responseJson = await response.json();
    if (response.ok) {
      if (responseJson.result != "success") {
        window.alert(responseJson.message);
        return;
      }
      setID0(responseJson.data.id0);
      checkJob();
    } else {
      applyMiiFormFeedback(responseJson.message);
    }
  }

  async function checkJob() {
    if (!id0) {
      showCard1();
      return;
    }
    const response = await fetch("{{ url_for('api_check_job_status', id0='') }}" + id0);
    const responseJson = await response.json();
    if (response.ok) {
      if (responseJson.result != "success") {
        window.alert(responseJson.message);
        return;
      }
      updateCards(responseJson.data.status);
      console.log(responseJson);
    } else {
      window.alert("Error checking job status: " + responseJson.message);
      startOver();
    }
  }

  async function cancelJob() {
    const response = await fetch("{{ url_for('api_cancel_job', id0='') }}" + id0);
    startOver();
  }


  document.addEventListener('DOMContentLoaded', () => {
    // event listeners
    cancelJobButton.addEventListener("click", event => cancelJob());
    doAnotherButton.addEventListener("click", event => startOver());
    miiForm.addEventListener("submit", event => {
      event.preventDefault();
      submitMiiForm();
    });
    miiUploadToggle.addEventListener("click", event => toggleMiiUpload());
    canceledModalEl.addEventListener("hide.bs.modal", event => startOver());
    failedModalEl.addEventListener("hide.bs.modal", event => startOver());

    // initial setup
    toggleMiiUpload();
    loadID0();
    checkJob();
  });

})();
