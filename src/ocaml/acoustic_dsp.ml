(** Phase 347: OCaml Acoustic DSP
    Functional signal processing for drone detection.
    FFT spectral analysis + peak detection + classification. *)

(* ── Types ──────────────────────────────────────────────────────── *)
type signal_type = Propeller | Engine | Wind | Speech | Unknown

type spectral_peak = {
  frequency : float;
  magnitude : float;
  phase : float;
}

type detection = {
  det_id : string;
  signal_type : signal_type;
  peaks : spectral_peak list;
  azimuth_deg : float;
  confidence : float;
}

(* ── Complex number ─────────────────────────────────────────────── *)
type complex = { re : float; im : float }

let complex_add a b = { re = a.re +. b.re; im = a.im +. b.im }
let complex_sub a b = { re = a.re -. b.re; im = a.im -. b.im }
let complex_mul a b = {
  re = a.re *. b.re -. a.im *. b.im;
  im = a.re *. b.im +. a.im *. b.re
}
let complex_mag c = sqrt (c.re *. c.re +. c.im *. c.im)
let complex_of_float x = { re = x; im = 0.0 }

(* ── FFT (Cooley-Tukey) ────────────────────────────────────────── *)
let rec fft signal =
  let n = Array.length signal in
  if n <= 1 then signal
  else begin
    let even = Array.init (n / 2) (fun i -> signal.(2 * i)) in
    let odd = Array.init (n / 2) (fun i -> signal.(2 * i + 1)) in
    let even_fft = fft even in
    let odd_fft = fft odd in
    let result = Array.make n { re = 0.0; im = 0.0 } in
    for k = 0 to n / 2 - 1 do
      let angle = -2.0 *. Float.pi *. float_of_int k /. float_of_int n in
      let twiddle = { re = cos angle; im = sin angle } in
      let t = complex_mul twiddle odd_fft.(k) in
      result.(k) <- complex_add even_fft.(k) t;
      result.(k + n / 2) <- complex_sub even_fft.(k) t
    done;
    result
  end

(* ── Hanning window ─────────────────────────────────────────────── *)
let hanning_window signal =
  let n = Array.length signal in
  Array.init n (fun i ->
    let w = 0.5 *. (1.0 -. cos (2.0 *. Float.pi *. float_of_int i /. float_of_int (n - 1))) in
    signal.(i) *. w)

(* ── Spectral Analysis ──────────────────────────────────────────── *)
let compute_spectrum signal sample_rate =
  let n = Array.length signal in
  let windowed = hanning_window signal in
  let complex_signal = Array.map complex_of_float windowed in
  let spectrum = fft complex_signal in
  let half_n = n / 2 + 1 in
  let freqs = Array.init half_n (fun i ->
    float_of_int i *. sample_rate /. float_of_int n) in
  let mags = Array.init half_n (fun i ->
    complex_mag spectrum.(i) /. float_of_int n) in
  (freqs, mags)

(* ── Peak Detection ─────────────────────────────────────────────── *)
let find_peaks freqs mags ?(threshold = 0.005) ?(max_peaks = 10) () =
  let n = Array.length mags in
  let peaks = ref [] in
  for i = 1 to n - 2 do
    if mags.(i) > mags.(i - 1) && mags.(i) > mags.(i + 1) && mags.(i) > threshold then
      peaks := { frequency = freqs.(i); magnitude = mags.(i); phase = 0.0 } :: !peaks
  done;
  let sorted = List.sort (fun a b -> compare b.magnitude a.magnitude) !peaks in
  List.filteri (fun i _ -> i < max_peaks) sorted

(* ── Signal Classification ──────────────────────────────────────── *)
let classify_signal peaks =
  match peaks with
  | [] -> Unknown
  | dominant :: rest ->
    let freq = dominant.frequency in
    if freq >= 50.0 && freq <= 500.0 then begin
      let harmonics = List.length (List.filter (fun p ->
        let ratio = p.frequency /. freq in
        abs_float (ratio -. Float.round ratio) < 0.1
      ) rest) in
      if harmonics >= 2 then Propeller else Engine
    end
    else if freq < 50.0 then Wind
    else if freq >= 300.0 && freq <= 3400.0 then Speech
    else Unknown

(* ── Signal Generator ───────────────────────────────────────────── *)
let generate_signal freq duration sample_rate =
  let n = int_of_float (duration *. sample_rate) in
  (* Ensure power of 2 for FFT *)
  let n2 = let rec p2 x = if x >= n then x else p2 (x * 2) in p2 1 in
  Array.init n2 (fun i ->
    if i < n then
      sin (2.0 *. Float.pi *. freq *. float_of_int i /. sample_rate)
    else 0.0)

(* ── Detection Engine ───────────────────────────────────────────── *)
let detect_counter = ref 0

let process_signal signal sample_rate =
  let (freqs, mags) = compute_spectrum signal sample_rate in
  let peaks = find_peaks freqs mags () in
  let sig_type = classify_signal peaks in
  match peaks with
  | [] -> None
  | _ ->
    incr detect_counter;
    Some {
      det_id = Printf.sprintf "ACO-%06d" !detect_counter;
      signal_type = sig_type;
      peaks = peaks;
      azimuth_deg = 0.0;
      confidence = List.fold_left (fun acc p -> acc +. p.magnitude) 0.0 peaks
                   |> min 1.0;
    }

let signal_type_to_string = function
  | Propeller -> "propeller"
  | Engine -> "engine"
  | Wind -> "wind"
  | Speech -> "speech"
  | Unknown -> "unknown"

(* ── Entry Point ────────────────────────────────────────────────── *)
let () =
  let sample_rate = 44100.0 in
  let freqs = [200.0; 440.0; 1000.0] in
  let results = List.filter_map (fun f ->
    let signal = generate_signal f 0.05 sample_rate in
    process_signal signal sample_rate
  ) freqs in
  List.iter (fun det ->
    Printf.printf "Detected: %s | Peaks: %d | Conf: %.4f\n"
      (signal_type_to_string det.signal_type)
      (List.length det.peaks)
      det.confidence
  ) results;
  Printf.printf "Total detections: %d\n" (List.length results)
