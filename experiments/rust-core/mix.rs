#![no_std]

// Packed RGB565 lanes use modulo-2^32 arithmetic, as in gfx_mix.
#[no_mangle]
pub extern "C" fn gfx_mix(a: u16, b: u16, t: i32) -> u16 {
    const MASK: u32 = 0x07e0_f81f;
    let lanes = |pixel: u16| {
        let p = u32::from(pixel);
        (p | (p << 16)) & MASK
    };
    let weight = t as u32;
    let sum = lanes(a).wrapping_mul(32u32.wrapping_sub(weight))
        .wrapping_add(lanes(b).wrapping_mul(weight));
    let mixed = (sum >> 5) & MASK;
    (mixed | (mixed >> 16)) as u16
}
