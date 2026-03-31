(* Phase 497: Cognitive Electronic Warfare (OCaml)
   스펙트럼 분석, 적응형 재밍 대응, 순수 함수형 신호 처리 *)

module Spectrum = struct
  type band =
    | VHF | UHF | L_Band | S_Band | C_Band | X_Band

  let band_range = function
    | VHF -> (30e6, 300e6)
    | UHF -> (300e6, 3e9)
    | L_Band -> (1e9, 2e9)
    | S_Band -> (2e9, 4e9)
    | C_Band -> (4e9, 8e9)
    | X_Band -> (8e9, 12e9)

  type sample = {
    frequency : float;
    power_dbm : float;
    timestamp : float;
    is_threat : bool;
  }

  let make_sample freq power ts threat =
    { frequency = freq; power_dbm = power; timestamp = ts; is_threat = threat }
end

module Threat = struct
  type attack_type =
    | Barrage_Jam | Spot_Jam | Sweep_Jam | Deceptive_Jam | Radar_Lock

  type countermeasure =
    | Freq_Hop | Spread_Spectrum | Power_Mgmt | Beam_Null | Decoy | Silence

  type threat_level = None | Low | Medium | High | Critical

  type assessment = {
    level : threat_level;
    attack : attack_type;
    confidence : float;
    countermeasure : countermeasure;
  }

  let level_to_int = function
    | None -> 0 | Low -> 1 | Medium -> 2 | High -> 3 | Critical -> 4

  let select_countermeasure = function
    | Barrage_Jam -> Spread_Spectrum
    | Spot_Jam -> Freq_Hop
    | Sweep_Jam -> Freq_Hop
    | Deceptive_Jam -> Decoy
    | Radar_Lock -> Silence

  let assess_level confidence =
    if confidence > 0.8 then Critical
    else if confidence > 0.6 then High
    else if confidence > 0.3 then Medium
    else if confidence > 0.1 then Low
    else None
end

module SignalAnalysis = struct
  let mean lst =
    let sum = List.fold_left (+.) 0.0 lst in
    sum /. float_of_int (List.length lst)

  let std_dev lst =
    let m = mean lst in
    let sq_diffs = List.map (fun x -> (x -. m) ** 2.0) lst in
    sqrt (mean sq_diffs)

  let detect_threats (samples : Spectrum.sample list) threshold =
    List.filter (fun (s : Spectrum.sample) -> s.power_dbm > threshold) samples

  let classify_jammer (threats : Spectrum.sample list) =
    match threats with
    | [] -> None
    | _ ->
      let freqs = List.map (fun (s : Spectrum.sample) -> s.frequency) threats in
      let min_f = List.fold_left min infinity freqs in
      let max_f = List.fold_left max neg_infinity freqs in
      let bandwidth = max_f -. min_f in
      let powers = List.map (fun (s : Spectrum.sample) -> s.power_dbm) threats in
      let avg_power = mean powers in
      if bandwidth > 500e6 then Some Threat.Barrage_Jam
      else if bandwidth < 10e6 && avg_power > -30.0 then Some Threat.Spot_Jam
      else if List.length threats > 3 then Some Threat.Sweep_Jam
      else Some Threat.Deceptive_Jam

  let compute_snr signal_power noise_floor = signal_power -. noise_floor

  let detect_jamming snr_db threshold =
    if snr_db < threshold then
      let confidence = Float.min 1.0 ((threshold -. snr_db) /. 20.0) in
      Some { Threat.level = Threat.assess_level confidence;
             attack = Threat.Signal_Jamming;
             confidence;
             countermeasure = Threat.Freq_Hop }
    else None

  (* FFT-based spectral analysis *)
  let rec fft (signal : (float * float) list) : (float * float) list =
    let n = List.length signal in
    if n <= 1 then signal
    else
      let even = List.filteri (fun i _ -> i mod 2 = 0) signal in
      let odd = List.filteri (fun i _ -> i mod 2 = 1) signal in
      let fft_even = fft even in
      let fft_odd = fft odd in
      let half = n / 2 in
      List.init n (fun k ->
        let angle = -2.0 *. Float.pi *. float_of_int k /. float_of_int n in
        let (or_, oi) = List.nth fft_odd (k mod half) in
        let (er, ei) = List.nth fft_even (k mod half) in
        let wr = cos angle in
        let wi = sin angle in
        let tr = wr *. or_ -. wi *. oi in
        let ti = wr *. oi +. wi *. or_ in
        (er +. tr, ei +. ti))

  let power_spectrum signal =
    let complex_signal = List.map (fun x -> (x, 0.0)) signal in
    let fft_result = fft complex_signal in
    List.map (fun (r, i) -> sqrt (r *. r +. i *. i)) fft_result
end

module CognitiveEW = struct
  type engagement = {
    threat_type : Threat.attack_type;
    countermeasure : Threat.countermeasure;
    success : bool;
    snr_improvement : float;
  }

  type state = {
    engagements : engagement list;
    total_threats : int;
    total_defended : int;
  }

  let init_state = { engagements = []; total_threats = 0; total_defended = 0 }

  let engage state threat_type confidence =
    let cm = Threat.select_countermeasure threat_type in
    let base_rate = match cm with
      | Threat.Freq_Hop -> 0.80
      | Threat.Spread_Spectrum -> 0.75
      | Threat.Power_Mgmt -> 0.60
      | Threat.Beam_Null -> 0.70
      | Threat.Decoy -> 0.65
      | Threat.Silence -> 0.90 in
    let success = confidence < base_rate in
    let snr_imp = if success then 15.0 else -2.0 in
    let eng = { threat_type; countermeasure = cm; success; snr_improvement = snr_imp } in
    { engagements = eng :: state.engagements;
      total_threats = state.total_threats + 1;
      total_defended = state.total_defended + (if success then 1 else 0) }

  let defense_rate state =
    if state.total_threats = 0 then 1.0
    else float_of_int state.total_defended /. float_of_int state.total_threats

  let avg_snr_improvement state =
    match state.engagements with
    | [] -> 0.0
    | engs ->
      let total = List.fold_left (fun acc e -> acc +. e.snr_improvement) 0.0 engs in
      total /. float_of_int (List.length engs)
end
