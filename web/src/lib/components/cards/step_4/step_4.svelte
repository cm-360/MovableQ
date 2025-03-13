<div class="card">
	<h4 class="card-header">Step 4: Obtain msed</h4>
	<div class="collapse" id="msedStepCollapse">
		<div class="card-body">
			<div class="d-grid gap-3 mb-3">
				<div class="card-text">
					Please wait for the mining process to complete. This process can take up to an hour, so
					feel free to leave this website running in the background, or even close it and come back
					later. While you wait, please ensure your ID0 is correct, and cancel the job if it is not.
				</div>
				<div>
					<span class="spinner-border spinner-border-sm" role="status"></span>
					<span id="msedStatus" class="m-2">Please wait...</span>
				</div>
				<div class="alert alert-dark mb-0" role="alert">
					<div>
						<div>ID0: <span id="msedId0"></span></div>
						<div>LFCS: <span id="msedLfcs"></span></div>
						<div>Assigned to: <span id="msedAssignee"></span></div>
					</div>
					<div class="mt-2 collapse" id="msedStatsCollapse">
						<div>Hash rate: <span id="msedStatHash">0</span> M/s</div>
						<div>Current offset: <span id="msedStatOffset"></span></div>
					</div>
				</div>
			</div>
			<button class="btn btn-danger" id="msedCancelButton">Cancel</button>
		</div>
	</div>
</div>
