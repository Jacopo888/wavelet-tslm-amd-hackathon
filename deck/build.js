const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "Wavelet-TSLM"; pres.author = "Jacopo D'Abundo";
const NAVY = "0B1220", LIGHT = "F4F6FA", RED = "ED1C24", GREY = "5B6B84", INK = "111827", MID = "9AA8BE", WHITE = "FFFFFF";
const F = "Calibri";
function base(dark, title, n, notes) {
  const s = pres.addSlide(); s.background = { color: dark ? NAVY : LIGHT };
  if (title) s.addText(title, { x: 0.6, y: 0.4, w: 12.1, h: 0.9, fontFace: F, fontSize: 36, bold: true, color: dark ? WHITE : INK, isTextBox: true, margin: 0 });
  s.addText(`Wavelet-TSLM · AMD Developer Hackathon: ACT III · Intelligent Industry     ${n}/8`, { x: 0.6, y: 7.0, w: 12.1, h: 0.3, fontFace: F, fontSize: 11, color: dark ? MID : GREY, isTextBox: true, margin: 0 });
  s.addNotes(notes); return s;
}
const card = () => ({ fill: { color: WHITE }, line: { color: "D5DBE6", width: 1 }, rectRadius: 0.1, shadow: { type: "outer", color: "000000", opacity: 0.12, blur: 6, offset: 2, angle: 90 } });
// 1
let s = base(true, null, 1, "Do you know what Time Series Language Models are? They are multimodal LLMs whose extra input is a time series. Until yesterday there were ChatTS, OpenTSLM, ITFormer and Toto. From today there is a new one: Wavelet-TSLM, my submission for this hackathon.");
s.addText("Wavelet-TSLM", { x: 0.8, y: 2.2, w: 11.5, h: 1.2, fontFace: F, fontSize: 66, bold: true, color: WHITE, isTextBox: true, margin: 0 });
s.addText("A new Time Series Language Model for long industrial telemetry", { x: 0.8, y: 3.5, w: 11.5, h: 0.7, fontFace: F, fontSize: 28, color: RED, bold: true, isTextBox: true, margin: 0 });
s.addText("Fine-tuned Qwen3.5-4B that reads temporal embeddings · runs on AMD Instinct MI300X (ROCm)\nTrack: Intelligent Industry · Team PoliMi · Jacopo D'Abundo", { x: 0.8, y: 4.5, w: 11.5, h: 1.2, fontFace: F, fontSize: 20, color: MID, isTextBox: true, margin: 0 });
// 2
s = base(false, "What is a Time Series Language Model?", 2, "A TSLM is a large language model whose multimodal input is a time series. The ones that existed until now: ChatTS, OpenTSLM-Flamingo and ITFormer, built on a frozen Chronos-2 encoder from Amazon and a Qwen3.5-4B backbone, and Toto, a 32B model.");
s.addText("An LLM whose multimodal input is a time series, not an image or text", { x: 0.6, y: 1.4, w: 12.1, h: 0.6, fontFace: F, fontSize: 22, color: GREY, isTextBox: true, margin: 0 });
s.addText("Until yesterday", { x: 0.6, y: 2.4, w: 6, h: 0.5, fontFace: F, fontSize: 22, bold: true, color: INK, isTextBox: true, margin: 0 });
[["ChatTS", "Qwen3.5-4B + Chronos-2"], ["OpenTSLM-Flamingo", "Qwen3.5-4B + Chronos-2"], ["ITFormer", "Qwen3.5-4B + Chronos-2"], ["Toto", "Qwen3-VL 32B, fine-tuned"]].forEach((c, i) => {
  const x = 0.6 + i * 3.1;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, Object.assign({ x, y: 3.0, w: 2.9, h: 1.8 }, card()));
  s.addText(c[0], { x: x + 0.2, y: 3.2, w: 2.5, h: 0.6, fontFace: F, fontSize: 20, bold: true, color: INK, isTextBox: true, margin: 0 });
  s.addText(c[1], { x: x + 0.2, y: 3.9, w: 2.5, h: 0.7, fontFace: F, fontSize: 14, color: GREY, isTextBox: true, margin: 0 });
});
s.addText("From today: Wavelet-TSLM", { x: 0.6, y: 5.4, w: 12.1, h: 0.8, fontFace: F, fontSize: 32, bold: true, color: RED, isTextBox: true, margin: 0 });
// 3
s = base(false, "Wavelet-TSLM: a Qwen that reads temporal embeddings", 3, "My submission is a fine-tuned Qwen adapted to receive temporal embeddings. A Haar-wavelet encoder turns the long series into tokens, a Qwen3.5-4B backbone with LoRA reasons over them, and a localization head returns where the anomaly starts and ends. It was trained only on synthetic anomalies from the AnomalyXL benchmark.");
[["Time series", "up to 131,072 samples\nper channel, many channels"], ["Haar-wavelet\nencoder", "multiscale, continuous\n(no text digits)"], ["Qwen3.5-4B\n+ LoRA", "fine-tuned backbone"], ["Localization\nhead", "channel, start, end\nof each anomaly"]].forEach((b, i) => {
  const x = 0.6 + i * 3.1;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 2.2, w: 2.7, h: 1.7, fill: { color: i === 2 ? RED : NAVY }, line: { color: i === 2 ? RED : NAVY, width: 1 }, rectRadius: 0.12 });
  s.addText(b[0], { x, y: 2.2, w: 2.7, h: 1.7, fontFace: F, fontSize: 22, bold: true, color: WHITE, align: "center", valign: "middle", isTextBox: true });
  s.addText(b[1], { x, y: 4.05, w: 2.7, h: 0.9, fontFace: F, fontSize: 14, color: GREY, align: "center", isTextBox: true, margin: 0 });
  if (i < 3) s.addText("→", { x: x + 2.7, y: 2.7, w: 0.4, h: 0.7, fontFace: F, fontSize: 32, bold: true, color: GREY, align: "center", isTextBox: true, margin: 0 });
});
s.addText("Trained only on synthetic anomalies (AnomalyXL, ETH Zürich) · one call reads the whole window", { x: 0.6, y: 5.6, w: 12.1, h: 0.6, fontFace: F, fontSize: 20, color: INK, isTextBox: true, margin: 0 });
// 4
s = base(false, "Benchmark against the other TSLMs (ETH Zürich)", 4, "Now the benchmarks, using the results of the ETH Zurich paper, TimeRLM, Table 1, without the agentic model. On localization my model scores 0.61 against 0.32 for the best TSLM, a 32 billion parameter Toto. The same on classification and multichannel. To be honest, on magnitude and lead-lag the baselines are better.");
const lab = ["Localize", "Classify", "Multichannel"];
s.addChart(pres.charts.BAR, [
  { name: "ChatTS", labels: lab, values: [0.003, 0.0, 0.0] }, { name: "OpenTSLM-Flamingo", labels: lab, values: [0.008, 0.0, 0.230] },
  { name: "ITFormer", labels: lab, values: [0.004, 0.001, 0.230] }, { name: "Toto 32B", labels: lab, values: [0.323, 0.072, 0.224] },
  { name: "Wavelet-TSLM", labels: lab, values: [0.606, 0.333, 0.752] }], {
  x: 0.6, y: 1.4, w: 12.1, h: 4.6, barDir: "col", barGrouping: "clustered", chartColors: [MID, "7F8EA8", "64748F", "3B4A66", RED],
  showLegend: true, legendPos: "b", legendFontSize: 14, legendFontFace: F, legendColor: INK, showValue: true, dataLabelFontSize: 11, dataLabelFontFace: F, dataLabelColor: INK, dataLabelFormatCode: "0.00",
  catAxisLabelFontSize: 16, catAxisLabelFontFace: F, catAxisLabelColor: INK, valAxisLabelFontSize: 12, valAxisLabelFontFace: F, valAxisLabelColor: GREY, valAxisMaxVal: 0.9, valAxisMinVal: 0,
  valGridLine: { color: "D5DBE6", size: 0.5 }, catGridLine: { style: "none" }, showTitle: true, title: "Official score, AnomalyXL test set (higher is better)", titleFontSize: 16, titleFontFace: F, titleColor: INK });
s.addText("Where we do not win: magnitude (0.31 vs Toto 0.82) and lead-lag (0.25 vs 0.35–0.56). ChatTS runs out of memory on multichannel. Baselines: Table 1, TimeRLM paper (arXiv 2608.03391). Ours: one call, no zoom, same scorer.", { x: 0.6, y: 6.15, w: 12.1, h: 0.75, fontFace: F, fontSize: 13, color: GREY, isTextBox: true, margin: 0 });
// 5
s = base(true, "Why are the others close to zero? Input length", 5, "You may ask why the others sit close to zero. This benchmark was built for series with hundreds of thousands of samples. In the public code the baseline TSLMs only see the last 8,192 samples of each channel, and ChatTS runs out of memory on multichannel. My model reads up to 131,072 samples per channel, sixteen times more. It is a design limit of those models, not a flaw: they were not built for this length.");
s.addText("16×", { x: 0.8, y: 1.7, w: 5.5, h: 2.4, fontFace: F, fontSize: 130, bold: true, color: RED, isTextBox: true, margin: 0 });
s.addText("more samples per channel\nin a single call", { x: 0.8, y: 4.2, w: 5.5, h: 1.0, fontFace: F, fontSize: 24, color: WHITE, isTextBox: true, margin: 0 });
s.addText([{ text: "Wavelet-TSLM reads up to 131,072 samples per channel", options: { bullet: true, breakLine: true } }, { text: "Baseline TSLMs see only the last 8,192 samples of each channel (Chronos-2 truncation)", options: { bullet: true, breakLine: true } }, { text: "ChatTS runs out of memory on multichannel input", options: { bullet: true, breakLine: true } }, { text: "The benchmark windows reach 131,072 samples: a design limit of those models, stated as fact", options: { bullet: true } }],
  { x: 6.8, y: 1.9, w: 5.9, h: 3.8, fontFace: F, fontSize: 20, color: WHITE, paraSpaceAfter: 14, isTextBox: true, margin: 0 });
// 6
s = base(false, "The only long-series rival: Zumarraga's agent", 6, "The only competitor on long series is the agentic model by Nicolas Zumarraga, TimeRLM. It is not a native time series language model: it is a Qwen without a temporal encoder working in a Python sandbox. Against its published numbers, same Qwen3.5-4B backbone after reinforcement learning, my model is higher on localization and on multichannel. It is lower on classification, magnitude and lead-lag. And on industrial windows we measured about seven turns and five minutes per window for the agent, against one call for mine.");
const lab2 = ["Localize", "Classify", "Magnitude", "Multichannel", "Lead-lag"];
s.addChart(pres.charts.BAR, [{ name: "TimeRLM agent (Qwen3.5-4B, after RL), published", labels: lab2, values: [0.538, 0.364, 0.510, 0.244, 0.687] }, { name: "Wavelet-TSLM (one call)", labels: lab2, values: [0.606, 0.333, 0.314, 0.752, 0.251] }], {
  x: 0.6, y: 1.4, w: 7.9, h: 4.9, barDir: "col", barGrouping: "clustered", chartColors: [MID, RED], showLegend: true, legendPos: "b", legendFontSize: 13, legendFontFace: F, legendColor: INK,
  showValue: true, dataLabelFontSize: 11, dataLabelFontFace: F, dataLabelColor: INK, dataLabelFormatCode: "0.00", catAxisLabelFontSize: 14, catAxisLabelFontFace: F, catAxisLabelColor: INK,
  valAxisLabelFontSize: 12, valAxisLabelFontFace: F, valAxisLabelColor: GREY, valAxisMaxVal: 0.9, valAxisMinVal: 0, valGridLine: { color: "D5DBE6", size: 0.5 }, catGridLine: { style: "none" } });
s.addText([{ text: "Not a native TSLM", options: { bold: true, breakLine: true } }, { text: "A Qwen without a temporal encoder, working with Python code in a sandbox", options: { breakLine: true } }, { text: " ", options: { breakLine: true } }, { text: "Cost on industrial windows", options: { bold: true, breakLine: true } }, { text: "Agent: about 7 turns and 5 minutes per window", options: { breakLine: true } }, { text: "Wavelet-TSLM: 1 call", options: { breakLine: true } }, { text: " ", options: { breakLine: true } }, { text: "Agents backed by GPT-5.5 score higher (localize 0.66–0.68)", options: { italic: true } }],
  { x: 8.8, y: 1.6, w: 3.9, h: 4.6, fontFace: F, fontSize: 16, color: INK, paraSpaceAfter: 4, isTextBox: true, margin: 0 });
// 7
s = base(false, "Zero-shot on a real plant: HAI 21.03", 7, "We then tested it on a real industrial control testbed, HAI 21.03, with no training on it: 38 windows of 9 hours and 16 channels, 50 documented attacks. The model touched 34 of the 50 attacks, against about 7 expected at random, and 60 percent of its intervals land on an attack, against 4.5 percent by chance. The limit: it also flags the windows without attacks, so it is a ranking of the most anomalous stretches, not an alarm. On MetroPT-3 it did not transfer.");
[["34 / 50", "attacks touched by an interval\n(about 7 expected at random)"], ["60 %", "of the intervals land on an attack\n(4.5 % at random)"], ["1 call", "per 9-hour, 16-channel window"]].forEach((c, i) => {
  const x = 0.6 + i * 4.1;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, Object.assign({ x, y: 1.6, w: 3.9, h: 2.9 }, card()));
  s.addText(c[0], { x, y: 1.8, w: 3.9, h: 1.4, fontFace: F, fontSize: 60, bold: true, color: RED, align: "center", isTextBox: true, margin: 0 });
  s.addText(c[1], { x: x + 0.2, y: 3.3, w: 3.5, h: 1.0, fontFace: F, fontSize: 16, color: GREY, align: "center", isTextBox: true, margin: 0 });
});
s.addText([{ text: "Honest limit: ", options: { bold: true } }, { text: "it also flags the 18 of 18 windows with no attack, so it ranks the most anomalous stretches; it is not an alarm. On MetroPT-3 (4 slow air-leak failures) it did not transfer." }],
  { x: 0.6, y: 4.9, w: 12.1, h: 1.2, fontFace: F, fontSize: 18, color: INK, isTextBox: true, margin: 0 });
// 8
s = base(true, "Built and measured on AMD", 8, "Everything ran on AMD: ROCm and Instinct MI300X. A FlexAttention kernel padded to 512 brings attention memory from 65.4 to 3.5 GiB at 16k context, measured on forward plus backward. The runs on the AMD Developer Cloud, four MI300X droplets, cost under ten dollars. Wavelet-TSLM: a new time series language model, on AMD. Thank you.");
s.addText("18.7×", { x: 0.8, y: 1.7, w: 5.5, h: 2.0, fontFace: F, fontSize: 110, bold: true, color: RED, isTextBox: true, margin: 0 });
s.addText("less attention memory at 16k context\n65.4 GiB → 3.5 GiB (forward + backward)", { x: 0.8, y: 3.9, w: 5.8, h: 1.1, fontFace: F, fontSize: 20, color: WHITE, isTextBox: true, margin: 0 });
s.addText([{ text: "PyTorch on ROCm 6.4, AMD Instinct MI300X", options: { bullet: true, breakLine: true } }, { text: "FlexAttention (Triton) padded to 512", options: { bullet: true, breakLine: true } }, { text: "4 MI300X droplets on the AMD Developer Cloud, under $10 in total", options: { bullet: true, breakLine: true } }, { text: "Same checkpoint, no retraining", options: { bullet: true } }],
  { x: 7.0, y: 1.9, w: 5.7, h: 3.2, fontFace: F, fontSize: 20, color: WHITE, paraSpaceAfter: 14, isTextBox: true, margin: 0 });
s.addText("Wavelet-TSLM: a new Time Series Language Model, on AMD. Thank you.", { x: 0.8, y: 5.6, w: 11.9, h: 0.8, fontFace: F, fontSize: 28, bold: true, color: WHITE, isTextBox: true, margin: 0 });
pres.writeFile({ fileName: "Wavelet-TSLM.pptx" }).then(f => console.log("scritto", f));
