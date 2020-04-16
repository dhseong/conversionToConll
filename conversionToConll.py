from typing import List, Dict, Any
import argparse
import glob
import json
import os
import re
from tqdm import tqdm


def return_annotated_text(morphs: List[str], iob_labels: List[str]) -> List[str]:
  """
  Args:
    morphs (List[str]): morphemes in a sentence
    iob_labels ([type]): labels formatted iob2 for a sentence
  Returns:
    List[str]: annotated morphemes
  """

  annotated_text = []
  for morph, label in zip(morphs, iob_labels):
    tmp_text = morph.split('\s')
    tmp_text[-1] = label
    tmp_text = '\s'.join(tmp_text)
    annotated_text.append(tmp_text)

  return annotated_text


def return_iob_labels(lengths: List[int], labels: List[List[Any]]) -> List[str]:
  """
  Args:
    lengths (List[int]): list of morph lengths in a morphs
    labels (List[List[Any]]): list of labels for morphs
  Returns:
    List[str]: labels for a morphs
  """

  iob_labels = []
  index = 0
  begin_flag = False
  labels.sort(key=lambda x: x[0])
  for length in lengths:
    if len(labels) > 0 \
      and labels[0][0] <= index \
        and labels[0][1] > index:
      if begin_flag:
        iob_labels.append('I-' + labels[0][2])
      else:
        iob_labels.append('B-' + labels[0][2])
        begin_flag = True
    else:
      iob_labels.append('O')
    index += length + 1
    if len(labels) > 0 and labels[0][1] <= index:
      labels = labels[1:]
      begin_flag = False
  return iob_labels


def reshape_json(json_file: str) -> Dict[str, Any]:
  """
  Args:
    json_file (str): json file formatted doccano output
  Returns:
    Dict[str, Any]: json contents of labeling result by doccano
  """

  with open(json_file, 'r', encoding='utf-8') as f:
    content = '['
    content += ''.join(
      [re.sub(r'}\n', '},\n', line)
        for line in f.readlines()]
    )[:-2] + ']'
  json_contents = json.loads(content)
  return json_contents


if __name__ == '__main__':
  parser = argparse.ArgumentParser(
    description='Parse doccano export and parsed \
      text to parsed text and labels.'
  )
  parser.add_argument('infile', type=str, 
                      help='a file path of doccano export')
  parser.add_argument('indir', type=str,
                      help='a directory path of parsed text')
  parser.add_argument('outdir', type=str,
                      help='a directory path of this program\'s result')
  args = parser.parse_args()

  os.makedirs(args.indir, exist_ok=True)
  os.makedirs(args.outdir, exist_ok=True)

  json_contents = reshape_json(args.infile)
  json_list = [json_content['text'] for json_content in json_contents]

  print('1. JSON1 file is loaded.\n   Total texts: {}'.format(len(json_list)))

  # create an parsed text
  i = 1
  for line in json_list:
    target_file = '{}/{}.txt'.format(
      args.indir, i
    )
    with open(target_file, 'w', encoding='utf-8') as f:
      f.write(line.replace(' ', '\n'))
    i = i + 1
  
  indir_files = glob.glob('{}/*.txt'.format(args.indir))

  print('2. Parsed texts are generated in {}.\n   indir_files: {}'.format(args.indir, len(indir_files)))

  for fname_indir in indir_files:
    with open(fname_indir, 'r', encoding='utf-8-sig') as f:
      parsed_morphs = f.readlines()
    morphs = [s.split('\n')[0] for s in parsed_morphs]
    synopsis_morphs = ' '.join(morphs)

    # make an annotated string
    morph_lengths = [len(morph) for morph in morphs]
    idx = json_list.index(synopsis_morphs)
    iob_labels = return_iob_labels(
      morph_lengths, json_contents[idx]['labels']
    )
    annotated_text = return_annotated_text(parsed_morphs, iob_labels)

    # create an annotated text
    target_file = '{}/{}'.format(
      args.outdir, fname_indir.replace(args.indir, '')
    )
    with open(target_file, 'w') as f:
      f.write('\n'.join(annotated_text))

  outdir_files = glob.glob('{}/*.txt'.format(args.outdir))

  print('3. Annotated texts are generated in {}\n   outdir_files: {}'.format(args.outdir, len(outdir_files)))

  morphs_indir = {}
  morphs_outdir = {}

  for fname_indir in indir_files:
    with open(fname_indir, 'r', encoding='utf-8-sig') as f_indir:
      parsed_morphs_indir = f_indir.readlines()
    morphs_indir[fname_indir.replace(args.indir, '').replace('\\', '').replace('.txt', '')] = [s.split('\n')[0] for s in parsed_morphs_indir]

  for fname_outdir in outdir_files:
    with open(fname_outdir, 'r', encoding='utf-8-sig') as f_outdir:
      parsed_morphs_outdir = f_outdir.readlines()
    morphs_outdir[fname_outdir.replace(args.outdir, '').replace('\\', '').replace('.txt', '')] = [s.split('\n')[0] for s in parsed_morphs_outdir]

  print('4. Generating CoNLL formatted file.')

  text = ''
  pbar = tqdm(total=len(json_list))
  for key in morphs_indir:
    pbar.update(1)
    if text == '':
      text = '-DOCSTART- O'
    else:
      text = text + '\n-DOCSTART- O'
    for index, value in enumerate(morphs_indir[key]):
      text = text + '\n' + morphs_indir[key][index]
      text = text + ' ' + morphs_outdir[key][index]
  pbar.close()

  text = text.replace('| O', '')

  target_file = '{}'.format(
    args.infile.replace('.json1', '_annotated.txt')
  )
  with open(target_file, 'w') as f:
    f.write(text)