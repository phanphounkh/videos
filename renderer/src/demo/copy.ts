/** All translatable text of the demo. UI mock-up labels stay English in both languages. */
export type Lang = 'en' | 'km';

export const COPY: Record<Lang, { titles: string[]; captions: string[]; cta: string }> = {
  en: {
    titles: ['Describe your idea', 'Generate', 'Edit', 'Organise & templates', 'Export'],
    captions: [
      'Turn an idea into a finished video.',
      'Describe your video in one sentence.',
      'Sorya writes the script, scenes and captions for you.',
      'Fine-tune everything in the editor: trim, add text, stickers and music.',
      'Keep projects in folders, star favourites, start from templates.',
      'Export a ready-to-share MP4 in one click.',
      'Start creating with Sorya.'
    ],
    cta: 'Start creating with Sorya'
  },
  km: {
    titles: ['ពណ៌នាគំនិតរបស់អ្នក', 'បង្កើតដោយស្វ័យប្រវត្តិ', 'កែសម្រួល', 'រៀបចំ និងគំរូ', 'នាំចេញ'],
    captions: [
      'បំប្លែងគំនិតទៅជាវីដេអូពេញលេញ។',
      'ពណ៌នាវីដេអូរបស់អ្នកក្នុងមួយប្រយោគ។',
      'Sorya សរសេរស្គ្រីប ឈុត និងចំណងជើងរងឱ្យអ្នក។',
      'កែសម្រួលគ្រប់យ៉ាងក្នុងកម្មវិធីកែ៖ កាត់ បន្ថែមអក្សរ ស្ទីកគ័រ និងតន្ត្រី។',
      'រក្សាគម្រោងក្នុងថត ដាក់ផ្កាយ និងចាប់ផ្តើមពីគំរូ។',
      'នាំចេញ MP4 ដែលរួចរាល់សម្រាប់ចែករំលែក ដោយចុចតែម្តង។',
      'ចាប់ផ្តើមបង្កើតជាមួយ Sorya។'
    ],
    cta: 'ចាប់ផ្តើមបង្កើតជាមួយ Sorya'
  }
};

/** [start, length] in frames; scenes overlap by OVERLAP frames for the transitions. */
export const OVERLAP = 14;
const LENGTHS = [120, 260, 250, 320, 200, 230, 130];
export const SCENES = LENGTHS.map((length, i) => {
  const start = LENGTHS.slice(0, i).reduce((s, l) => s + l - OVERLAP, 0);
  return { start, length };
});
export const DEMO_FRAMES = SCENES[SCENES.length - 1].start + SCENES[SCENES.length - 1].length;
