<div class="card">
	<h4 class="card-header">Step 1: Choose a Method</h4>
	<div class="collapse" id="methodStepCollapse">
		<form id="methodForm" class="card-body">
			<div class="mb-3 row g-3" id="methodCardGroup">
				<div class="col-md-6">
					<div class="card btn p-0 text-start focus-ring border-success" id="methodCardFc">
						<div class="card-body">
							<input
								type="radio"
								class="btn-check"
								name="methodRadio"
								id="methodButtonFc"
								value="fc-lfcs"
								checked
							/>
							<h5 class="card-title"><label for="methodButtonFc">Friend Code Mining</label></h5>
							<p class="card-text">
								This uses the data obtained from a two-way friend exchange as a starting point for
								bruteforcing.
							</p>
						</div>
					</div>
				</div>
				<div class="col-md-6">
					<div
						class="card btn p-0 text-start focus-ring border-secondary-subtle"
						id="methodCardMii"
					>
						<div class="card-body">
							<input
								type="radio"
								class="btn-check"
								name="methodRadio"
								id="methodButtonMii"
								value="mii-lfcs"
							/>
							<h5 class="card-title"><label for="methodButtonMii">Mii Mining</label></h5>
							<p class="card-text">
								This uses a Mii QR code instead of a two-way friend exchange, but is significantly
								more time-consuming.
							</p>
						</div>
					</div>
				</div>
				<!-- part1: This uses the user provided movable_part1.sed as a starting point for bruteforcing. -->
			</div>
			<button type="submit" class="btn btn-success"
				>Get started <i class="fa-solid fa-arrow-right"></i></button
			>
		</form>
	</div>
</div>
