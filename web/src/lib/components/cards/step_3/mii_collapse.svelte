<div class="collapse" id="miiLfcsStepCollapse">
	<div class="card-body">
		<div class="d-grid gap-3 mb-3">
			<div class="card-text">
				Please wait for the mining process to complete. This process can take up to 90 minutes, so
				feel free to leave this website running in the background, or even close it and come back
				later.
			</div>
			<div>
				<span class="spinner-border spinner-border-sm" role="status"></span>
				<span id="miiLfcsStatus" class="m-2">Please wait...</span>
			</div>
			<div class="alert alert-dark mb-0" role="alert">
				<div>
					<div>System ID: <span id="miiLfcsSysId"></span></div>
					<div>Assigned to: <span id="miiLfcsAssignee"></span></div>
				</div>
				<div class="mt-2 collapse" id="miiLfcsStatsCollapse">
					<div>Hash rate: <span id="miiLfcsStatHash">0</span> M/s</div>
					<div>Current offset: <span id="miiLfcsStatOffset"></span></div>
				</div>
			</div>
		</div>
		<button class="btn btn-danger" id="miiLfcsCancelButton">Cancel</button>
	</div>
</div>
