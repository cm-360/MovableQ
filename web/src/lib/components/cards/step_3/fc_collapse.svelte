<div class="collapse" id="fcLfcsStepCollapse">
	<div class="card-body">
		<div class="alert alert-info" role="alert">
			Using the 3DS friends list, regsiter <b id="botFriendCode">????-????-????</b> as a new online
			friend. Feel free to enter any name you wish, it is not important. If you need assistance
			adding a friend, check Nintendo's instructions
			<a
				class="link"
				href="https://www.nintendo.co.uk/Support/Nintendo-3DS-2DS/FAQ/Hardware/How-do-I-register-friends-/How-do-I-register-friends-242795.html"
				>here</a
			>.
		</div>
		<div class="d-grid gap-3 mb-3">
			<div class="card-text">
				It is connected to this service and will automatically retrieve your <code
					>movable_part1.sed</code
				> when you add it to your friend list. Add the friend code provided above and just wait for it
				to process, this site should proceed automatically.
			</div>
			<div>
				<span class="spinner-border spinner-border-sm" role="status"></span>
				<span class="ms-2" id="fcLfcsStatus">Please wait...</span>
			</div>
			<div class="card-text">
				Alternatively, you can manually obtain <code>movable_part1.sed</code> by using
				<a class="link" href="https://github.com/zoogie/seedminer/releases/tag/v2.1">seedStarter</a>
				on a second, already-modded console. If you choose to do so, upload the file
				<a
					data-bs-toggle="collapse"
					href="#fcLfcsForm"
					role="button"
					aria-expanded="false"
					aria-controls="fcLfcsForm">here</a
				>.
			</div>
			<form id="fcLfcsForm" class="collapse">
				<div class="mb-3">
					<label class="form-label" for="lfcs_file">Movable part1 file</label>
					<input
						type="file"
						class="form-control collapse"
						id="lfcs_file"
						name="lfcs_file"
						accept=".sed"
					/>
					<input
						type="text"
						class="form-control collapse"
						id="lfcs_url"
						name="lfcs_url"
						placeholder="https://example.com/path/to/movable_part1.sed"
					/>
					<div class="invalid-feedback">Your part1 data is invalid.</div>
					<button type="button" class="btn btn-link btn-sm p-0" id="lfcsUploadToggle"></button>
				</div>
				<button type="submit" class="btn btn-success">Submit</button>
			</form>
		</div>
		<button class="btn btn-danger" id="fcLfcsCancelButton">Cancel</button>
	</div>
</div>
