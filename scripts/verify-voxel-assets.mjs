import { createReadStream } from 'node:fs';
import { readFile, stat } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { Readable } from 'node:stream';
import { createGunzip } from 'node:zlib';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const manifests = await Promise.all(['voxel', 'teaching'].map(async name => JSON.parse(await readFile(resolve(root, `scripts/${name}/assets.json`), 'utf8'))));
async function digest(stream) {
  const hash = createHash('sha256');
  for await (const chunk of stream) hash.update(chunk);
  return hash.digest('hex');
}
try {
  for (const manifest of manifests) {
  for (const source of [manifest.source, ...(manifest.sources || [])]) {
    const actual = source.normalization === 'lf'
      ? createHash('sha256').update((await readFile(resolve(root, source.path), 'utf8')).replaceAll('\r\n', '\n')).digest('hex')
      : await digest(createReadStream(resolve(root, source.path)));
    if (actual !== source.sha256)
      throw new Error(`Model source checksum mismatch: ${source.path}`);
  }
  for (const model of manifest.models) {
    for (const file of model.files) {
      if ((await stat(resolve(root, file))).size >= 25 * 1024 * 1024)
        throw new Error(`Asset exceeds hosting file limit: ${file}`);
    }
    async function* chunks() {
      for (const file of model.files) yield* createReadStream(resolve(root, file));
    }
    const input = Readable.from(chunks());
    const decoded = createGunzip();
    input.on('error', error => decoded.destroy(error));
    input.pipe(decoded);
    if (await digest(decoded) !== model.decompressedSHA256)
      throw new Error(`Reconstructed geometry checksum mismatch: ${model.files[0]}`);
  }
  }
  console.log('Verified source files and all mouse model checksums.');
} catch (error) {
  console.error(error.message);
  console.error('To generate model assets, follow scripts/voxel/README.md, then run npm run build again.');
  process.exitCode = 1;
}
