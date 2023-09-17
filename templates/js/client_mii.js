import { getCookie, setCookie } from "{{ url_for('serve_js', filename='utils.js') }}";

(() => {

  let mii;
  let id0;
  let intervalId = 0;

  const card1 = new bootstrap.Collapse(document.getElementById("card1"), { toggle: false });
  const card2 = new bootstrap.Collapse(document.getElementById("card2"), { toggle: false });
  const card3 = new bootstrap.Collapse(document.getElementById("card3"), { toggle: false });

  const miiForm = document.getElementById("miiForm");

  const miiUploadToggle = document.getElementById("miiUploadToggle");
  const miiUploadFile = document.getElementById("mii_file");
  const miiUploadUrl = document.getElementById("mii_url");

  const miningMii = document.getElementById("miningMii");
  const miningId0 = document.getElementById("miningId0");
  const miningStatus = document.getElementById("miningStatus");
  const miningMiiAssignee = document.getElementById("miningMiiAssignee");
  const miningId0Assignee = document.getElementById("miningId0Assignee");
  const miningStatsCollapse = document.getElementById("miningStatsCollapse");
  const miningRate = document.getElementById("miningRate");
  const miningOffset = document.getElementById("miningOffset");
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

  function showCard2(statusResponse) {
    if (mii)
      miningMii.innerText = mii;
    miningId0.innerText = id0;
    // mining stats
    const miningStats = statusResponse.mining_stats;
    (mii ? miningMiiAssignee : miningId0Assignee).innerText = miningStats.assignee;
    if (miningStats.rate && miningStats.offset) {
      miningRate.innerText = miningStats.rate;
      miningOffset.innerText = miningStats.offset;
      miningStatsCollapse.classList.add("show");
    } else {
      miningStatsCollapse.classList.remove("show");
    }
    // spinner message
    switch (statusResponse.status) {
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

  function updateCards(statusResponse) {
    switch (statusResponse.status) {
      case "done":
        if (mii) {
          setMii();
          checkJob();
        } else {
          showCard3();
        }
        break;
      case "waiting":
      case "working":
        showCard2(statusResponse);
        break;
      case "canceled":
        cancelJobWatch();
        canceledModal.show();
        break;
      case "failed":
        cancelJobWatch();
        // TODO failure note
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
    for (let invalid of feedback.replace("invalid:", "").split(",")) {
      if (invalid == "mii") {
        miiForm.elements["mii_file"].classList.add("is-invalid");
        miiForm.elements["mii_url"].classList.add("is-invalid");
      } else {
        miiForm.elements[invalid].classList.add("is-invalid");
      }
    }
  }


  // actions

  function loadID0() {
    const urlParams = new URLSearchParams(window.location.search);
    let tmp_id0;
    if (urlParams.has("id0")) {
      tmp_id0 = urlParams.get("id0");
    } else {
      tmp_id0 = getCookie("id0");
    }
    if (tmp_id0.length == 32) {
      setID0(tmp_id0);
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

  function loadMii() {
    const urlParams = new URLSearchParams(window.location.search);
    let tmp_mii;
    if (urlParams.has("mii")) {
      tmp_mii = urlParams.get("mii");
    } else {
      tmp_mii = getCookie("mii");
    }
    if (tmp_mii.length == 16) {
      setMii(tmp_mii);
    }
  }

  function setMii(new_mii) {
    if (new_mii) {
      const urlParams = new URLSearchParams(window.location.search);
      urlParams.set("mii", new_mii);
      window.history.pushState(new_mii, "", window.location.pathname + "?" + urlParams.toString());
    } else {
      // avoid adding duplicate blank history entries
      if (mii) {
        window.history.pushState(new_mii, "", window.location.pathname);
      }
    }
    mii = new_mii;
    setCookie("mii", mii, 7);
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
    setMii("");
    setID0("");
    cancelJobWatch();
    resetMiiFormFeedback();
    showCard1();
  }

  async function submitMiiForm() {
    const formData = new FormData(miiForm);    
    // fetch mii data if selected
    if (miiUploadUrl.classList.contains("show")) {
      try {
        const miiResponse = await fetch(miiUploadUrl.value);
        const miiBlob = await miiResponse.blob();
        formData.set("mii_file", miiBlob);
      } catch (error) {
        window.alert(`Error downloading Mii data: ${error.message}`);
        return;
      }
    }
    // submit job to server
    let response;
    try {
      response = await fetch("{{ url_for('api_submit_mii_job') }}", {
        method: "POST",
        body: formData
      });
      const responseJson = await response.json();
      if (response.ok) {
        // submission successful
        setMii(responseJson.data.mii);
        setID0(responseJson.data.id0);
        checkJob();
      } else {
        // throw error with server message
        throw new Error(responseJson.message);
      }
    } catch (error) {
      if (error instanceof SyntaxError) {
        // syntax error from parsing non-JSON server error response
        window.alert(`Error submitting job: ${response.status} - ${response.statusText}`);
      } else if (error.message.startsWith("invalid:")) {
        // form input invalid
        applyMiiFormFeedback(error.message);
      } else if (error.message === "Duplicate job") {
        // duplicate job
        if (window.confirm("A job with this ID0 already exists. Would you like to view its progress?")) {
          setID0(formData.get("id0"));
          checkJob();
        }
      } else {
        // generic error
        window.alert(`Error submitting job: ${error.message}`);
      }
    }
  }

  async function checkJob() {
    const key = mii || id0;
    if (!key) {
      showCard1();
      return;
    }
    // grab job status from server
    let response;
    try {
      response = await fetch(`{{ url_for('api_check_job_status', key='') }}${key}?include_stats=1`);
      const responseJson = await response.json();
      if (response.ok) {
        updateCards(responseJson.data);
        console.log(responseJson);
      } else {
        throw new Error(responseJson.message);
      }
    } catch (error) {
      if (error instanceof SyntaxError) {
        // syntax error from parsing non-JSON server error response
        window.alert(`Error checking job status: ${response.status} - ${response.statusText}`);
      } else if (error.message.includes("KeyError")) {
        const kn = key === mii ? "Mii" : "ID0";
        window.alert(`Error checking job status: ${kn} ${key} not found`);
      } else {
        // generic error
        window.alert(`Error checking job status: ${error.message}`);
      }
      // do not reset the page for network errors!
      if (error.message.startsWith("NetworkError")) {
        return;
      }
      startOver();
    }
  }

  async function cancelJob() {
    const key = mii || id0;
    let response;
    try {
      response = await fetch("{{ url_for('api_cancel_job', key='') }}" + key);
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
    loadMii();
    loadID0();
    checkJob();
  });

})();
