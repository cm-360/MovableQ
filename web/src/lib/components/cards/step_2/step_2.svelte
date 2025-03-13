<div class="card">
	<h4 class="card-header">Step 2: Console Information</h4>
	<div class="collapse" id="fcSubmitStepCollapse">
		<form id="fcJobForm" class="card-body">
			<div class="d-grid gap-3 mb-3">
				<div class="card-text">
					This section is for <b>friend code mining</b>. To get started, enter your console's
					information into the boxes below.
				</div>
				<div>
					<label for="fc_id0" class="form-label">ID0</label>
					<input
						required
						type="text"
						class="form-control"
						id="fc_id0"
						name="id0"
						placeholder="a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5"
					/>
					<div class="invalid-feedback">
						Your ID0 should be a 32-character hex string. Also make sure it's not an ID1 (the 2nd
						level folder name).
					</div>
				</div>
				<div>
					<label for="fc_friend_code" class="form-label">Friend code</label>
					<input
						required
						type="text"
						class="form-control"
						id="fc_friend_code"
						name="friend_code"
						placeholder="123456789012"
					/>
					<div class="invalid-feedback">This is not a valid friend code.</div>
				</div>
			</div>
			<button type="submit" class="btn btn-success">Submit</button>
			<button type="button" class="btn btn-secondary" id="fcJobBackButton">Back</button>
		</form>
	</div>
	<div class="collapse" id="miiSubmitStepCollapse">
		<form id="miiJobForm" class="card-body">
			<div class="d-grid gap-3 mb-3">
				<div class="card-text">
					This section is for <b>Mii mining</b>. To get started, enter your console's information
					into the boxes below. Your console's manufacturing year will be estimated from the
					specific model you select. If you happen to know the exact manufacturing year, you may
					also override the automatic estimate.
				</div>
				<div>
					<label for="mii_id0" class="form-label">ID0</label>
					<input
						required
						type="text"
						class="form-control"
						id="mii_id0"
						name="id0"
						placeholder="a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5"
					/>
					<div class="invalid-feedback">
						Your ID0 should be a 32-character hex string. Also make sure it's not an ID1 (the 2nd
						level folder name).
					</div>
				</div>
				<div>
					<label for="mii_model" class="form-label">Model</label>
					<select required id="mii_model" class="form-control" name="model">
						<option selected disabled value="">Choose...</option>
						<option value="old,2011">Old 3DS</option>
						<option value="old,2013">Old 3DS XL</option>
						<option value="old,2015">Old 2DS</option>
						<option value="new,2016">New 3DS</option>
						<option value="new,2016">New 3DS XL</option>
						<option value="new,2017">New 2DS XL</option>
					</select>
					<div class="invalid-feedback">Please choose your device's model.</div>
					<button
						type="button"
						class="btn btn-link btn-sm p-0"
						data-bs-toggle="collapse"
						data-bs-target="#miiConsoleYearCollapse"
						role="button"
						aria-expanded="false"
						aria-controls="miiConsoleYearCollapse">Override manufacturing year</button
					>
				</div>
				<div class="collapse" id="miiConsoleYearCollapse">
					<label for="mii_year" class="form-label">Manufacturing year</label>
					<input
						type="number"
						class="form-control"
						id="mii_year"
						name="year"
						min="2011"
						max="2020"
						value=""
						placeholder="20XX"
					/>
					<div class="invalid-feedback">Please enter a year between 2011-2020, or leave blank.</div>
				</div>
				<div>
					<!-- TODO fix for attribute on label to work for both file and URL (wrap in div?) -->
					<label for="mii_file" class="form-label">Mii QR code</label>
					<input
						type="file"
						class="form-control collapse"
						id="mii_file"
						name="mii_file"
						accept=".jpg,.bin"
					/>
					<input
						type="text"
						class="form-control collapse"
						id="mii_url"
						name="mii_url"
						placeholder="https://example.com/path/to/HNI_XXXX.JPG"
					/>
					<div class="invalid-feedback">Your Mii data is invalid.</div>
					<button type="button" class="btn btn-link btn-sm p-0" id="miiUploadToggle"></button>
				</div>
			</div>
			<button type="submit" class="btn btn-success">Submit</button>
			<button type="button" class="btn btn-secondary" id="miiJobBackButton">Back</button>
		</form>
	</div>
</div>
