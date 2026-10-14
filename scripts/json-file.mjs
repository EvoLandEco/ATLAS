
import {JSONParser} from '@streamparser/json';

export function parseJsonBytes(bytes) {
  const parser = new JSONParser({paths:['$'], stringBufferSize:64 * 1024});
  let value;
  parser.onValue = result => { value = result.value; };
  for (let offset=0; offset<bytes.length; offset+=1024*1024) parser.write(bytes.subarray(offset,offset+1024*1024));
  if (!parser.isEnded) parser.end();
  if (value === undefined) throw new SyntaxError('JSON file contains no value');
  return value;
}
