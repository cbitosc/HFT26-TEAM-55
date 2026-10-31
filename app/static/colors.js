export const languageColors={TypeScript:'#2478d4',JavaScript:'#b58105',Python:'#25854a',Rust:'#b85b35',Shell:'#158579',Java:'#df5733','C#':'#9a4fba',Go:'#008da8',CSS:'#7554ca',HTML:'#e35e32',Ruby:'#cc3555',PHP:'#6c61b5',Kotlin:'#b54d9c',Swift:'#d86522','C++':'#386fc4',C:'#6376a4','Text/configuration':'#147f94'};
export const flowColors=['#237ce5','#12a57a','#e58a18','#be51c4','#e15070','#149eb4'];
export const languageColor=language=>languageColors[language]||'#596fa2';
export function fileLanguage(path=''){const ext=path.split('.').pop().toLowerCase();return ({ts:'TypeScript',tsx:'TypeScript',js:'JavaScript',jsx:'JavaScript',mjs:'JavaScript',py:'Python',rs:'Rust',sh:'Shell',bash:'Shell',java:'Java',cs:'C#',go:'Go',css:'CSS',scss:'CSS',html:'HTML',rb:'Ruby',php:'PHP',kt:'Kotlin',swift:'Swift',cpp:'C++',cc:'C++',c:'C',h:'C'})[ext]||'Text/configuration';}
export const fileColor=path=>languageColor(fileLanguage(path));
