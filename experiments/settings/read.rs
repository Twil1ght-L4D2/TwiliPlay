#![no_std]

/// For a matching length, a non-null pointer must address three readable bytes
/// in the live Epsilon record. The caller keeps the record alive for this call.
#[no_mangle]
pub unsafe extern "C" fn tw_theme_id(data: *const [u8; 3], length: u32) -> i32 {
    if length != 3 || data.is_null() {
        return -1;
    }
    match unsafe { *data } {
        [b'T', 1, id] => i32::from(id),
        _ => -1,
    }
}

/// Same lifetime contract, with a two-byte record. Missing or unknown
/// preferences use the launcher's original animations-on default.
#[no_mangle]
pub unsafe extern "C" fn tw_motion(data: *const [u8; 2], length: u32) -> bool {
    length != 2 || data.is_null() || unsafe { *data } != [1, 0]
}
